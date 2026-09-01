"""Evidence-backed baseline events derived from track observations."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from .models import Observation, TimelineEvent


def detect_track_events(observations: List[Observation]) -> List[TimelineEvent]:
    grouped: Dict[int, List[Observation]] = defaultdict(list)
    for observation in observations:
        grouped[observation.track_id].append(observation)

    events = []
    for track_id, track in grouped.items():
        ordered = sorted(track, key=lambda item: item.timestamp_seconds)
        first, last = ordered[0], ordered[-1]
        events.append(
            TimelineEvent(
                "object_enters_scene",
                first.timestamp_seconds,
                track_id,
                f"{first.class_name.title()} track {track_id} first appears",
                first.confidence,
                first.frame_path,
            )
        )
        events.append(
            TimelineEvent(
                "object_exits_scene",
                last.timestamp_seconds,
                track_id,
                f"{last.class_name.title()} track {track_id} last appears",
                last.confidence,
                last.frame_path,
            )
        )
    return sorted(events, key=lambda item: item.timestamp_seconds)

