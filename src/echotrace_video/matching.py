"""Explainable cross-camera track matching candidates."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from math import hypot
from pathlib import Path
from typing import Dict, List, Sequence, Tuple


def _track_features(evidence: Dict[str, object]) -> List[Dict[str, object]]:
    path = evidence.get("analysis_path")
    if not path or not Path(str(path)).is_file():
        return []
    analysis = json.loads(Path(str(path)).read_text(encoding="utf-8"))
    metadata = analysis.get("metadata", {})
    width = max(float(metadata.get("width", 1)), 1)
    height = max(float(metadata.get("height", 1)), 1)
    grouped = defaultdict(list)
    for item in analysis.get("observations", []):
        grouped[(item["track_id"], item["class_name"])].append(item)
    tracks = []
    offset = float(evidence["effective_offset"])
    for (track_id, class_name), observations in grouped.items():
        ordered = sorted(observations, key=lambda item: item["timestamp_seconds"])
        boxes = [item["box"] for item in ordered]
        aspects = [(box[2] - box[0]) / max(box[3] - box[1], 1e-9) for box in boxes]
        areas = [((box[2] - box[0]) / width) * ((box[3] - box[1]) / height) for box in boxes]
        first_center = ((boxes[0][0] + boxes[0][2]) / 2, (boxes[0][1] + boxes[0][3]) / 2)
        last_center = ((boxes[-1][0] + boxes[-1][2]) / 2, (boxes[-1][1] + boxes[-1][3]) / 2)
        tracks.append(
            {
                "evidence_id": evidence["evidence_id"],
                "source": evidence["original_filename"],
                "track_id": track_id,
                "class_name": class_name,
                "global_start": float(ordered[0]["timestamp_seconds"]) + offset,
                "global_end": float(ordered[-1]["timestamp_seconds"]) + offset,
                "mean_aspect": sum(aspects) / len(aspects),
                "mean_area": sum(areas) / len(areas),
                "motion": (
                    (last_center[0] - first_center[0]) / width,
                    (last_center[1] - first_center[1]) / height,
                ),
                "confidence": sum(float(item["confidence"]) for item in ordered) / len(ordered),
            }
        )
    return tracks


def _similarity(first: float, second: float) -> float:
    return max(0.0, 1.0 - abs(first - second) / max(abs(first), abs(second), 1e-9))


def _motion_similarity(first: Tuple[float, float], second: Tuple[float, float]) -> float:
    first_norm, second_norm = hypot(*first), hypot(*second)
    if first_norm < 1e-6 or second_norm < 1e-6:
        return 0.5
    cosine = (first[0] * second[0] + first[1] * second[1]) / (first_norm * second_norm)
    return (cosine + 1) / 2


def match_tracks(evidence_items: Sequence[Dict[str, object]]) -> List[Dict[str, object]]:
    tracks = [track for evidence in evidence_items for track in _track_features(evidence)]
    matches = []
    for first_index, first in enumerate(tracks):
        for second in tracks[first_index + 1 :]:
            if first["evidence_id"] == second["evidence_id"]:
                continue
            if first["class_name"] != second["class_name"]:
                continue
            aspect = _similarity(float(first["mean_aspect"]), float(second["mean_aspect"]))
            area = _similarity(float(first["mean_area"]), float(second["mean_area"]))
            time_gap = max(
                0.0,
                float(first["global_start"]) - float(second["global_end"]),
                float(second["global_start"]) - float(first["global_end"]),
            )
            temporal = max(0.0, 1.0 - time_gap / 10)
            motion = _motion_similarity(first["motion"], second["motion"])
            probability = round(
                min(float(first["confidence"]), float(second["confidence"]))
                * (0.3 * aspect + 0.2 * area + 0.35 * temporal + 0.15 * motion),
                4,
            )
            identity = ":".join(
                sorted(
                    (
                        f"{first['evidence_id']}:{first['track_id']}",
                        f"{second['evidence_id']}:{second['track_id']}",
                    )
                )
            )
            matches.append(
                {
                    "match_id": hashlib.sha256(identity.encode()).hexdigest()[:16],
                    "first": {
                        key: first[key]
                        for key in ("evidence_id", "source", "track_id", "class_name")
                    },
                    "second": {
                        key: second[key]
                        for key in ("evidence_id", "source", "track_id", "class_name")
                    },
                    "probability": probability,
                    "signals": {
                        "shape_similarity": round(aspect, 4),
                        "relative_size_similarity": round(area, 4),
                        "temporal_overlap": round(temporal, 4),
                        "motion_similarity": round(motion, 4),
                    },
                    "review_status": "needs_review",
                }
            )
    return sorted(matches, key=lambda item: item["probability"], reverse=True)
