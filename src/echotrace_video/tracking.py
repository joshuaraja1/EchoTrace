"""Small deterministic IoU tracker suitable for the Phase 1 baseline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from .models import Detection


def intersection_over_union(
    first: Tuple[float, float, float, float], second: Tuple[float, float, float, float]
) -> float:
    x1, y1 = max(first[0], second[0]), max(first[1], second[1])
    x2, y2 = min(first[2], second[2]), min(first[3], second[3])
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    first_area = max(0.0, first[2] - first[0]) * max(0.0, first[3] - first[1])
    second_area = max(0.0, second[2] - second[0]) * max(0.0, second[3] - second[1])
    return intersection / max(first_area + second_area - intersection, 1e-9)


@dataclass
class _TrackState:
    class_name: str
    box: Tuple[float, float, float, float]
    missed: int = 0


class IoUTracker:
    def __init__(self, threshold: float = 0.25, max_missed: int = 2) -> None:
        self.threshold = threshold
        self.max_missed = max_missed
        self._tracks: Dict[int, _TrackState] = {}
        self._next_id = 1

    def update(self, detections: List[Detection]) -> List[Tuple[int, Detection]]:
        unmatched_tracks = set(self._tracks)
        assignments = []
        for detection in sorted(detections, key=lambda item: item.confidence, reverse=True):
            candidates = [
                (intersection_over_union(state.box, detection.box), track_id)
                for track_id, state in self._tracks.items()
                if track_id in unmatched_tracks and state.class_name == detection.class_name
            ]
            score, track_id = max(candidates, default=(0.0, -1))
            if score < self.threshold:
                track_id = self._next_id
                self._next_id += 1
            self._tracks[track_id] = _TrackState(detection.class_name, detection.box)
            unmatched_tracks.discard(track_id)
            assignments.append((track_id, detection))

        for track_id in unmatched_tracks:
            self._tracks[track_id].missed += 1
        self._tracks = {
            track_id: state
            for track_id, state in self._tracks.items()
            if state.missed <= self.max_missed
        }
        return assignments

