"""Phase 2 synchronization signal extraction and confidence fusion."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from .audio import AudioExtractionError, extract_audio
from .synchronizer import estimate_offset


@dataclass(frozen=True)
class SyncSignal:
    method: str
    offset_seconds: float
    confidence: float
    diagnostics: Dict[str, object]

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class FusedSynchronization:
    offset_seconds: float
    confidence: float
    signals: Sequence[SyncSignal]
    warning: Optional[str]

    def to_dict(self) -> Dict[str, object]:
        return {
            "offset_seconds": self.offset_seconds,
            "confidence": self.confidence,
            "signals": [signal.to_dict() for signal in self.signals],
            "warning": self.warning,
        }


def metadata_signal(reference: Dict[str, object], target: Dict[str, object]) -> Optional[SyncSignal]:
    reference_time = reference.get("creation_time")
    target_time = target.get("creation_time")
    if not reference_time or not target_time:
        return None
    try:
        reference_dt = datetime.fromisoformat(str(reference_time).replace("Z", "+00:00"))
        target_dt = datetime.fromisoformat(str(target_time).replace("Z", "+00:00"))
    except ValueError:
        return None
    offset = (target_dt - reference_dt).total_seconds()
    return SyncSignal(
        "metadata_timestamp",
        offset,
        0.95,
        {"reference_creation_time": str(reference_time), "target_creation_time": str(target_time)},
    )


def audio_signal(
    reference_path: Path,
    target_path: Path,
    sample_rate: int = 8_000,
    max_offset_seconds: float = 60.0,
) -> Optional[SyncSignal]:
    try:
        reference = extract_audio(reference_path, sample_rate)
        target = extract_audio(target_path, sample_rate)
    except AudioExtractionError:
        return None
    estimate = estimate_offset(reference, target, sample_rate, max_offset_seconds)
    return SyncSignal(
        "audio_gcc_phat",
        estimate.offset_seconds,
        estimate.confidence,
        {"peak_ratio": estimate.peak_ratio, "peak_z_score": estimate.peak_z_score},
    )


def _normalized_correlation_offset(
    reference: np.ndarray, target: np.ndarray, sample_rate: float, max_offset_seconds: float
) -> Tuple[float, float]:
    if reference.size < 3 or target.size < 3:
        raise ValueError("motion series are too short")
    reference = (reference - np.mean(reference)) / max(float(np.std(reference)), 1e-9)
    target = (target - np.mean(target)) / max(float(np.std(target)), 1e-9)
    correlation = np.correlate(reference, target, mode="full")
    lags = np.arange(-(target.size - 1), reference.size)
    allowed = np.abs(lags) <= round(max_offset_seconds * sample_rate)
    correlation = correlation[allowed]
    lags = lags[allowed]
    strength = np.abs(correlation)
    peak_index = int(np.argmax(strength))
    peak = float(strength[peak_index])
    competitors = strength.copy()
    guard = max(1, round(sample_rate))
    competitors[max(0, peak_index - guard) : peak_index + guard + 1] = 0
    ratio = peak / max(float(np.max(competitors)), 1e-9)
    confidence = float(np.clip((ratio - 1) / 2, 0, 1))
    return float(lags[peak_index] / sample_rate), confidence


def visual_motion_signal(
    reference_analysis: Dict[str, object],
    target_analysis: Dict[str, object],
    max_offset_seconds: float = 60.0,
) -> Optional[SyncSignal]:
    reference_frames = reference_analysis.get("frame_analysis", [])
    target_frames = target_analysis.get("frame_analysis", [])
    if not isinstance(reference_frames, list) or not isinstance(target_frames, list):
        return None
    reference = np.array([frame.get("motion_score", 0) for frame in reference_frames], dtype=float)
    target = np.array([frame.get("motion_score", 0) for frame in target_frames], dtype=float)
    sample_rate = float(reference_analysis.get("sample_fps", 0))
    if sample_rate <= 0 or np.std(reference) < 1e-6 or np.std(target) < 1e-6:
        return None
    try:
        offset, confidence = _normalized_correlation_offset(
            reference, target, sample_rate, max_offset_seconds
        )
    except ValueError:
        return None
    return SyncSignal(
        "visual_motion_correlation",
        offset,
        confidence,
        {"sample_fps": sample_rate, "reference_samples": len(reference), "target_samples": len(target)},
    )


def trajectory_event_signal(
    reference_analysis: Dict[str, object],
    target_analysis: Dict[str, object],
    max_offset_seconds: float = 60.0,
) -> Optional[SyncSignal]:
    """Estimate alignment from shared trajectory-derived event landmarks."""
    eligible = {
        "vehicle_changes_direction",
        "vehicle_stops",
        "rapid_deceleration",
        "paths_converge",
        "potential_impact",
        "post_impact_stop",
    }
    reference_by_type = {
        str(event["event_type"]): event
        for event in reference_analysis.get("timeline", [])
        if event.get("event_type") in eligible
    }
    target_by_type = {
        str(event["event_type"]): event
        for event in target_analysis.get("timeline", [])
        if event.get("event_type") in eligible
    }
    shared = sorted(set(reference_by_type) & set(target_by_type))
    offsets = [
        float(reference_by_type[event_type]["timestamp_seconds"])
        - float(target_by_type[event_type]["timestamp_seconds"])
        for event_type in shared
    ]
    offsets = [value for value in offsets if abs(value) <= max_offset_seconds]
    if not offsets:
        return None
    offset = float(np.median(offsets))
    spread = float(np.median(np.abs(np.array(offsets) - offset)))
    agreement = float(np.exp(-spread))
    coverage = min(1.0, len(offsets) / 3)
    confidence = round(0.7 * agreement * coverage, 4)
    return SyncSignal(
        "trajectory_event_alignment",
        round(offset, 6),
        confidence,
        {"shared_event_types": shared, "offset_candidates": offsets, "spread": spread},
    )


def fuse_signals(signals: Sequence[SyncSignal]) -> FusedSynchronization:
    usable = [signal for signal in signals if signal.confidence > 0]
    if not usable:
        return FusedSynchronization(0.0, 0.0, signals, "No reliable synchronization signal")
    ordered = sorted(usable, key=lambda signal: signal.offset_seconds)
    total_weight = sum(signal.confidence for signal in ordered)
    cumulative = 0.0
    offset = ordered[-1].offset_seconds
    for signal in ordered:
        cumulative += signal.confidence
        if cumulative >= total_weight / 2:
            offset = signal.offset_seconds
            break
    weighted_deviations = sorted(
        (abs(signal.offset_seconds - offset), signal.confidence) for signal in usable
    )
    deviation_weight = 0.0
    robust_deviation = weighted_deviations[-1][0]
    for deviation, weight in weighted_deviations:
        deviation_weight += weight
        if deviation_weight >= total_weight / 2:
            robust_deviation = deviation
            break
    consistency = float(np.exp(-robust_deviation))
    coverage = min(1.0, len(usable) / 2)
    base = float(np.average([signal.confidence for signal in usable]))
    confidence = round(float(np.clip(base * consistency * (0.75 + 0.25 * coverage), 0, 1)), 4)
    warning = None if confidence >= 0.5 else "Synchronization requires investigator review"
    return FusedSynchronization(round(offset, 6), confidence, signals, warning)


def synchronize_pair(
    reference: Dict[str, object], target: Dict[str, object], max_offset_seconds: float = 60.0
) -> FusedSynchronization:
    signals: List[SyncSignal] = []
    metadata = metadata_signal(
        dict(reference.get("metadata") or {}), dict(target.get("metadata") or {})
    )
    if metadata:
        signals.append(metadata)
    audio = audio_signal(
        Path(str(reference["storage_path"])),
        Path(str(target["storage_path"])),
        max_offset_seconds=max_offset_seconds,
    )
    if audio:
        signals.append(audio)
    reference_analysis = _load_analysis(reference.get("analysis_path"))
    target_analysis = _load_analysis(target.get("analysis_path"))
    visual = visual_motion_signal(reference_analysis, target_analysis, max_offset_seconds)
    if visual:
        signals.append(visual)
    trajectory = trajectory_event_signal(
        reference_analysis, target_analysis, max_offset_seconds
    )
    if trajectory:
        signals.append(trajectory)
    return fuse_signals(signals)


def _load_analysis(path: object) -> Dict[str, object]:
    if not path or not Path(str(path)).is_file():
        return {}
    return json.loads(Path(str(path)).read_text(encoding="utf-8"))
