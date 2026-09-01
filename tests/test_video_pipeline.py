from pathlib import Path

from echotrace_video.events import detect_track_events
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
