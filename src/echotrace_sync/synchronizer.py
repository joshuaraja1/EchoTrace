"""Offset estimation with explicit uncertainty diagnostics."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Optional

import numpy as np

from .audio import extract_audio


@dataclass(frozen=True)
class SyncEstimate:
    offset_seconds: float
    confidence: float
    peak_ratio: float
    peak_z_score: float
    method: str = "audio_gcc_phat"
    warning: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def _next_power_of_two(value: int) -> int:
    return 1 << (value - 1).bit_length()


def estimate_offset(
    reference: np.ndarray,
    target: np.ndarray,
    sample_rate: int,
    max_offset_seconds: Optional[float] = None,
) -> SyncEstimate:
    """Estimate target offset where global time equals target local time plus offset."""
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    if reference.size < 2 or target.size < 2:
        raise ValueError("reference and target must contain at least two samples")

    correlation_size = reference.size + target.size - 1
    fft_size = _next_power_of_two(correlation_size)
    reference_fft = np.fft.rfft(reference, fft_size)
    target_fft = np.fft.rfft(target, fft_size)
    cross_power = reference_fft * np.conj(target_fft)
    cross_power /= np.maximum(np.abs(cross_power), 1e-12)
    circular = np.fft.irfft(cross_power, fft_size)
    correlation = np.concatenate((circular[-(target.size - 1) :], circular[: reference.size]))
    lags = np.arange(-(target.size - 1), reference.size)

    if max_offset_seconds is not None:
        if max_offset_seconds <= 0:
            raise ValueError("max_offset_seconds must be positive")
        max_lag = round(max_offset_seconds * sample_rate)
        allowed = np.abs(lags) <= max_lag
        correlation = correlation[allowed]
        lags = lags[allowed]

    strength = np.abs(correlation)
    peak_index = int(np.argmax(strength))
    peak = float(strength[peak_index])
    guard = max(1, round(0.05 * sample_rate))
    competitors = strength.copy()
    competitors[max(0, peak_index - guard) : peak_index + guard + 1] = 0.0
    second_peak = float(np.max(competitors)) if competitors.size else 0.0
    peak_ratio = peak / max(second_peak, 1e-12)
    median = float(np.median(strength))
    mad = float(np.median(np.abs(strength - median)))
    peak_z_score = (peak - median) / max(1.4826 * mad, 1e-12)

    ratio_score = np.clip((peak_ratio - 1.0) / 2.0, 0.0, 1.0)
    z_score = np.clip((peak_z_score - 3.0) / 12.0, 0.0, 1.0)
    confidence = float(0.55 * ratio_score + 0.45 * z_score)
    warning = None if confidence >= 0.5 else "Weak or ambiguous shared audio; review manually"

    return SyncEstimate(
        offset_seconds=float(lags[peak_index] / sample_rate),
        confidence=round(confidence, 4),
        peak_ratio=round(peak_ratio, 4),
        peak_z_score=round(peak_z_score, 4),
        warning=warning,
    )


def synchronize_files(
    files: Iterable[Path],
    reference: Path,
    sample_rate: int = 8_000,
    max_offset_seconds: Optional[float] = None,
) -> Dict[str, object]:
    """Synchronize media files against one reference and return a JSON-ready manifest."""
    paths = [Path(path).resolve() for path in files]
    reference = Path(reference).resolve()
    if reference not in paths:
        raise ValueError("reference must be one of the input files")
    if len(set(paths)) != len(paths):
        raise ValueError("input files must be unique")

    decoded = {path: extract_audio(path, sample_rate) for path in paths}
    sources: Dict[str, object] = {}
    for path in paths:
        if path == reference:
            estimate = SyncEstimate(0.0, 1.0, 1.0, 0.0, method="reference")
        else:
            estimate = estimate_offset(
                decoded[reference], decoded[path], sample_rate, max_offset_seconds
            )
        sources[str(path)] = estimate.to_dict()

    return {
        "schema_version": "1.0",
        "reference": str(reference),
        "offset_convention": "global_time = local_media_time + offset_seconds",
        "sample_rate_hz": sample_rate,
        "sources": sources,
    }
