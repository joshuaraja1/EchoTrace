import json
from pathlib import Path

from echotrace_timeline import build_unified_timeline


def evidence(tmp_path: Path, identifier: str, offset: float, events):
    analysis_path = tmp_path / f"{identifier}.json"
    analysis_path.write_text(json.dumps({"timeline": events}), encoding="utf-8")
    return {
        "evidence_id": identifier,
        "original_filename": f"{identifier}.mp4",
        "analysis_path": str(analysis_path),
        "effective_offset": offset,
    }


def test_timeline_maps_local_time_and_preserves_citation(tmp_path: Path):
    item = evidence(
        tmp_path,
        "camera-a",
        7.0,
        [
            {
                "event_type": "object_enters_scene",
                "timestamp_seconds": 2.5,
                "description": "Car appears",
                "confidence": 0.9,
                "track_id": 1,
                "frame_path": "frame.jpg",
            }
        ],
    )
    timeline = build_unified_timeline([item])
    event = timeline["events"][0]
    assert event["global_timestamp_seconds"] == 9.5
    assert event["evidence"][0]["local_timestamp_seconds"] == 2.5
    assert event["evidence"][0]["frame_path"] == "frame.jpg"
    assert event["event_id"]


def test_only_cross_source_incident_events_are_merged(tmp_path: Path):
    first = evidence(
        tmp_path,
        "a",
        0,
        [
            {
                "event_type": "potential_impact",
                "timestamp_seconds": 5,
                "description": "Possible impact",
                "confidence": 0.8,
            },
            {
                "event_type": "object_enters_scene",
                "timestamp_seconds": 2,
                "description": "Car appears",
                "confidence": 0.9,
            },
        ],
    )
    second = evidence(
        tmp_path,
        "b",
        1,
        [
            {
                "event_type": "potential_impact",
                "timestamp_seconds": 4.2,
                "description": "Possible impact",
                "confidence": 0.85,
            },
            {
                "event_type": "object_enters_scene",
                "timestamp_seconds": 1,
                "description": "Truck appears",
                "confidence": 0.9,
            },
        ],
    )
    timeline = build_unified_timeline([first, second])
    impacts = [event for event in timeline["events"] if event["event_type"] == "potential_impact"]
    entries = [
        event for event in timeline["events"] if event["event_type"] == "object_enters_scene"
    ]
    assert len(impacts) == 1
    assert impacts[0]["evidence_count"] == 2
    assert len(entries) == 2
