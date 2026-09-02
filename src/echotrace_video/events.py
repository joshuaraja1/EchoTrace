"""Evidence-backed baseline events derived from track observations."""

from __future__ import annotations

from collections import defaultdict
from math import atan2, degrees, hypot
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
        if len(ordered) >= 3:
            centers = [
                ((item.box[0] + item.box[2]) / 2, (item.box[1] + item.box[3]) / 2)
                for item in ordered
            ]
            speeds = []
            for index in range(1, len(ordered)):
                elapsed = ordered[index].timestamp_seconds - ordered[index - 1].timestamp_seconds
                if elapsed > 0:
                    speeds.append(
                        hypot(
                            centers[index][0] - centers[index - 1][0],
                            centers[index][1] - centers[index - 1][1],
                        )
                        / elapsed
                    )
            if len(speeds) >= 2 and speeds[-1] <= 2.0 and speeds[-2] <= 2.0:
                events.append(
                    TimelineEvent(
                        "vehicle_stops",
                        last.timestamp_seconds,
                        track_id,
                        f"{last.class_name.title()} track {track_id} may have stopped",
                        min(last.confidence, 0.75),
                        last.frame_path,
                    )
                )
            vectors = [
                (centers[index][0] - centers[index - 1][0], centers[index][1] - centers[index - 1][1])
                for index in range(1, len(centers))
            ]
            for index in range(1, len(vectors)):
                if hypot(*vectors[index - 1]) < 2 or hypot(*vectors[index]) < 2:
                    continue
                first_angle = degrees(atan2(vectors[index - 1][1], vectors[index - 1][0]))
                second_angle = degrees(atan2(vectors[index][1], vectors[index][0]))
                change = abs((second_angle - first_angle + 180) % 360 - 180)
                if change >= 60:
                    evidence = ordered[index + 1]
                    events.append(
                        TimelineEvent(
                            "vehicle_changes_direction",
                            evidence.timestamp_seconds,
                            track_id,
                            f"{evidence.class_name.title()} track {track_id} may have changed direction",
                            min(evidence.confidence, 0.7),
                            evidence.frame_path,
                        )
                    )
                    break
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
