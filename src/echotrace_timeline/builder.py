"""Phase 3 local-to-global event mapping with evidence citations."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Sequence

MERGEABLE_EVENT_TYPES = {"potential_impact", "paths_converge", "post_impact_stop"}


def _event_id(event_type: str, timestamp: float, evidence_ids: Sequence[str]) -> str:
    value = f"{event_type}:{timestamp:.3f}:{':'.join(sorted(evidence_ids))}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _load_events(evidence: Dict[str, object]) -> List[Dict[str, object]]:
    path = evidence.get("analysis_path")
    if not path or not Path(str(path)).is_file():
        return []
    analysis = json.loads(Path(str(path)).read_text(encoding="utf-8"))
    offset = float(evidence["effective_offset"])
    events = []
    for raw_event in analysis.get("timeline", []):
        local_time = float(raw_event["timestamp_seconds"])
        confidence = float(raw_event.get("confidence", 0))
        citation = {
            "evidence_id": evidence["evidence_id"],
            "source": evidence["original_filename"],
            "local_timestamp_seconds": local_time,
            "global_timestamp_seconds": round(local_time + offset, 6),
            "frame_path": raw_event.get("frame_path"),
            "confidence": confidence,
        }
        events.append(
            {
                "event_type": raw_event["event_type"],
                "global_timestamp_seconds": round(local_time + offset, 6),
                "description": raw_event["description"],
                "confidence": confidence,
                "track_id": raw_event.get("track_id"),
                "evidence": [citation],
                "review_status": "unreviewed",
            }
        )
    return events


def _can_merge(first: Dict[str, object], second: Dict[str, object], window: float) -> bool:
    if first["event_type"] != second["event_type"]:
        return False
    if first["event_type"] not in MERGEABLE_EVENT_TYPES:
        return False
    first_sources = {item["evidence_id"] for item in first["evidence"]}
    second_sources = {item["evidence_id"] for item in second["evidence"]}
    return not first_sources.intersection(second_sources) and abs(
        float(first["global_timestamp_seconds"]) - float(second["global_timestamp_seconds"])
    ) <= window


def build_unified_timeline(
    evidence_items: Sequence[Dict[str, object]], merge_window_seconds: float = 0.75
) -> Dict[str, object]:
    if merge_window_seconds <= 0:
        raise ValueError("merge_window_seconds must be positive")
    candidates = sorted(
        (event for evidence in evidence_items for event in _load_events(evidence)),
        key=lambda event: float(event["global_timestamp_seconds"]),
    )
    merged: List[Dict[str, object]] = []
    for candidate in candidates:
        match = next(
            (event for event in reversed(merged) if _can_merge(event, candidate, merge_window_seconds)),
            None,
        )
        if match is None:
            merged.append(candidate)
            continue
        combined_evidence = match["evidence"] + candidate["evidence"]
        weights = [max(float(item["confidence"]), 0.01) for item in combined_evidence]
        match["global_timestamp_seconds"] = round(
            sum(
                float(item["global_timestamp_seconds"])
                * weight
                for item, weight in zip(combined_evidence, weights)
            )
            / sum(weights),
            6,
        )
        match["confidence"] = round(
            min(0.99, max(float(match["confidence"]), float(candidate["confidence"])) + 0.05),
            4,
        )
        match["description"] = (
            f"{str(match['event_type']).replace('_', ' ').title()} supported by "
            f"{len(combined_evidence)} sources"
        )
        match["evidence"] = combined_evidence

    for event in merged:
        ids = [str(item["evidence_id"]) for item in event["evidence"]]
        event["event_id"] = _event_id(
            str(event["event_type"]), float(event["global_timestamp_seconds"]), ids
        )
        event["evidence_count"] = len(event["evidence"])
    return {
        "clock": "unified_incident_time_seconds",
        "source_count": len(evidence_items),
        "event_count": len(merged),
        "events": merged,
    }
