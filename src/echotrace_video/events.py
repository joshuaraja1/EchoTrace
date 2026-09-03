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


def detect_interaction_events(observations: List[Observation]) -> List[TimelineEvent]:
    """Detect cautious trajectory and overlap candidates within one camera."""
    by_timestamp: Dict[float, List[Observation]] = defaultdict(list)
    by_track: Dict[int, List[Observation]] = defaultdict(list)
    for observation in observations:
        by_timestamp[observation.timestamp_seconds].append(observation)
        by_track[observation.track_id].append(observation)
    events = []
    impact_tracks = set()
    vehicle_types = {"car", "truck", "motorcycle", "bicycle"}
    for timestamp, frame_observations in sorted(by_timestamp.items()):
        vehicles = [item for item in frame_observations if item.class_name in vehicle_types]
        for first_index, first in enumerate(vehicles):
            for second in vehicles[first_index + 1 :]:
                x_overlap = max(0.0, min(first.box[2], second.box[2]) - max(first.box[0], second.box[0]))
                y_overlap = max(0.0, min(first.box[3], second.box[3]) - max(first.box[1], second.box[1]))
                overlap = x_overlap * y_overlap
                first_area = max(1.0, (first.box[2] - first.box[0]) * (first.box[3] - first.box[1]))
                second_area = max(1.0, (second.box[2] - second.box[0]) * (second.box[3] - second.box[1]))
                overlap_ratio = overlap / min(first_area, second_area)
                if overlap_ratio >= 0.08:
                    confidence = min(first.confidence, second.confidence, 0.82)
                    events.append(
                        TimelineEvent(
                            "potential_impact",
                            timestamp,
                            first.track_id,
                            f"Possible overlap between tracks {first.track_id} and {second.track_id}",
                            confidence,
                            first.frame_path,
                        )
                    )
                    impact_tracks.update((first.track_id, second.track_id))

    track_items = list(by_track.items())
    for first_index, (first_id, first_track) in enumerate(track_items):
        for second_id, second_track in track_items[first_index + 1 :]:
            first_by_time = {item.timestamp_seconds: item for item in first_track}
            second_by_time = {item.timestamp_seconds: item for item in second_track}
            shared = sorted(set(first_by_time).intersection(second_by_time))
            if len(shared) < 3:
                continue
            distances = []
            for timestamp in shared:
                first = first_by_time[timestamp]
                second = second_by_time[timestamp]
                first_center = ((first.box[0] + first.box[2]) / 2, (first.box[1] + first.box[3]) / 2)
                second_center = ((second.box[0] + second.box[2]) / 2, (second.box[1] + second.box[3]) / 2)
                distances.append(hypot(first_center[0] - second_center[0], first_center[1] - second_center[1]))
            if distances[-1] < distances[0] * 0.65 and all(
                later <= earlier * 1.15 for earlier, later in zip(distances, distances[1:])
            ):
                evidence = first_by_time[shared[-1]]
                events.append(
                    TimelineEvent(
                        "paths_converge",
                        shared[-1],
                        first_id,
                        f"Tracks {first_id} and {second_id} appear to converge",
                        min(evidence.confidence, second_by_time[shared[-1]].confidence, 0.76),
                        evidence.frame_path,
                    )
                )

    for track_id, track in by_track.items():
        ordered = sorted(track, key=lambda item: item.timestamp_seconds)
        if len(ordered) < 4:
            continue
        speeds = []
        for first, second in zip(ordered, ordered[1:]):
            elapsed = second.timestamp_seconds - first.timestamp_seconds
            first_center = ((first.box[0] + first.box[2]) / 2, (first.box[1] + first.box[3]) / 2)
            second_center = ((second.box[0] + second.box[2]) / 2, (second.box[1] + second.box[3]) / 2)
            speeds.append(
                hypot(second_center[0] - first_center[0], second_center[1] - first_center[1])
                / max(elapsed, 1e-9)
            )
        for index in range(1, len(speeds)):
            if speeds[index - 1] >= 8 and speeds[index] <= speeds[index - 1] * 0.35:
                evidence = ordered[index + 1]
                events.append(
                    TimelineEvent(
                        "rapid_deceleration",
                        evidence.timestamp_seconds,
                        track_id,
                        f"Track {track_id} may have rapidly decelerated",
                        min(evidence.confidence, 0.72),
                        evidence.frame_path,
                    )
                )
                if track_id in impact_tracks and speeds[index] <= 2:
                    events.append(
                        TimelineEvent(
                            "post_impact_stop",
                            evidence.timestamp_seconds,
                            track_id,
                            f"Track {track_id} may have stopped after a possible impact",
                            min(evidence.confidence, 0.7),
                            evidence.frame_path,
                        )
                    )
                break
    unique = {}
    for event in events:
        key = (event.event_type, round(event.timestamp_seconds, 3), event.description)
        unique[key] = event
    return sorted(unique.values(), key=lambda item: item.timestamp_seconds)
