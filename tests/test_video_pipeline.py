from pathlib import Path

from echotrace_video.events import detect_interaction_events, detect_track_events
from echotrace_video.models import Detection, Observation
from echotrace_video.tracking import IoUTracker, intersection_over_union


def test_iou_and_tracker_preserve_identity():
    tracker = IoUTracker(threshold=0.2)
    first = tracker.update([Detection("car", 0.9, (10, 10, 50, 50))])
    second = tracker.update([Detection("car", 0.88, (14, 12, 54, 52))])
    assert intersection_over_union((10, 10, 50, 50), (14, 12, 54, 52)) > 0.7
    assert first[0][0] == second[0][0]


def test_tracker_does_not_match_different_classes():
    tracker = IoUTracker()
    car_id = tracker.update([Detection("car", 0.9, (0, 0, 20, 20))])[0][0]
    person_id = tracker.update([Detection("person", 0.9, (0, 0, 20, 20))])[0][0]
    assert car_id != person_id


def test_events_include_evidence_paths():
    observations = [
        Observation(0.5, str(Path("frame_1.jpg")), 1, "car", 0.9, (0, 0, 10, 10)),
        Observation(1.0, str(Path("frame_2.jpg")), 1, "car", 0.85, (1, 0, 11, 10)),
    ]
    events = detect_track_events(observations)
    assert [event.event_type for event in events] == ["object_enters_scene", "object_exits_scene"]
    assert events[0].frame_path.endswith("frame_1.jpg")


def test_events_detect_possible_stop_and_direction_change():
    stopped = [
        Observation(index, f"frame_{index}.jpg", 1, "car", 0.9, (10, 10, 30, 30))
        for index in range(3)
    ]
    turning = [
        Observation(0, "a.jpg", 2, "car", 0.9, (0, 0, 10, 10)),
        Observation(1, "b.jpg", 2, "car", 0.9, (10, 0, 20, 10)),
        Observation(2, "c.jpg", 2, "car", 0.9, (10, 10, 20, 20)),
    ]
    event_types = {event.event_type for event in detect_track_events(stopped + turning)}
    assert "vehicle_stops" in event_types
    assert "vehicle_changes_direction" in event_types


def test_interaction_events_detect_convergence_and_possible_impact():
    observations = []
    for timestamp, first_x, second_x in ((0, 0, 80), (1, 20, 60), (2, 38, 42)):
        observations.extend(
            [
                Observation(timestamp, f"f{timestamp}.jpg", 1, "car", 0.9, (first_x, 0, first_x + 20, 20)),
                Observation(timestamp, f"f{timestamp}.jpg", 2, "truck", 0.88, (second_x, 0, second_x + 20, 20)),
            ]
        )
    event_types = {event.event_type for event in detect_interaction_events(observations)}
    assert "paths_converge" in event_types
    assert "potential_impact" in event_types
