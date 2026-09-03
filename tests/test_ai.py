from echotrace_ai.context import filter_context_to_events
from echotrace_ai.graph import build_evidence_graph
from echotrace_ai.reasoning import LocalEvidenceReasoner


def sample_context():
    event = {
        "event_id": "impact-1",
        "event_type": "potential_impact",
        "global_timestamp_seconds": 12.5,
        "description": "Potential impact detected",
        "confidence": 0.86,
        "evidence": [
            {
                "evidence_id": "camera-a",
                "source": "camera-a.mp4",
                "local_timestamp_seconds": 5.5,
                "global_timestamp_seconds": 12.5,
                "frame_path": "frame.jpg",
                "confidence": 0.86,
            }
        ],
    }
    return {
        "investigation": {"investigation_id": "inv-1", "title": "Collision"},
        "sources": [],
        "timeline": {"events": [event], "event_count": 1},
        "policy": {"no_fault_or_liability": True},
    }


def test_local_reasoner_returns_evidence_citations():
    context = sample_context()
    reasoner = LocalEvidenceReasoner()
    summary = reasoner.summarize(context)
    answer = reasoner.answer("When was the potential impact?", context)
    assert summary["citations"][0]["event_id"] == "impact-1"
    assert answer["citations"][0]["evidence"][0]["evidence_id"] == "camera-a"
    assert "does not assign fault" in answer["warning"]


def test_local_reasoner_calculates_time_before_impact():
    context = sample_context()
    context["timeline"]["events"].insert(
        0,
        {
            "event_id": "converge-1",
            "event_type": "paths_converge",
            "global_timestamp_seconds": 7.5,
            "description": "Vehicle paths appear to converge",
            "confidence": 0.75,
            "evidence": context["timeline"]["events"][0]["evidence"],
        },
    )
    answer = LocalEvidenceReasoner().answer(
        "What happened five seconds before impact?", context
    )
    assert "5 seconds before it is T+7.50s" in answer["answer"]
    assert answer["citations"][0]["event_id"] == "converge-1"


def test_local_reasoner_lists_video_sources_for_observed_vehicle():
    context = sample_context()
    context["sources"] = [
        {
            "evidence_id": "camera-a",
            "filename": "camera-a.mp4",
            "effective_offset_seconds": 7.0,
        }
    ]
    context["objects"] = [
        {
            "evidence_id": "camera-a",
            "track_id": 1,
            "class_name": "car",
            "canonical_identity": "Vehicle A",
            "timestamp_seconds": 5.5,
            "confidence": 0.86,
            "frame_url": "/frame.jpg",
        }
    ]
    answer = LocalEvidenceReasoner().answer("Which videos show Vehicle A?", context)
    assert "camera-a.mp4" in answer["answer"]
    assert answer["citations"][0]["frame_url"] == "/frame.jpg"


def test_context_filter_never_introduces_unknown_events():
    filtered = filter_context_to_events(sample_context(), ["impact-1", "fabricated"])
    assert [event["event_id"] for event in filtered["timeline"]["events"]] == ["impact-1"]


def test_evidence_graph_connects_event_to_source():
    context = sample_context()
    evidence = [
        {
            "evidence_id": "camera-a",
            "original_filename": "camera-a.mp4",
            "processing_status": "analyzed",
            "sha256": "abc",
        }
    ]
    graph = build_evidence_graph(
        context["investigation"], evidence, context["timeline"]
    )
    relations = {edge["relation"] for edge in graph["edges"]}
    assert relations == {"contains", "supported_by"}


def test_evidence_graph_includes_tracked_objects_and_matches():
    graph = build_evidence_graph(
        {"investigation_id": "case-1", "title": "Test"},
        [
            {
                "evidence_id": "cam-a",
                "original_filename": "a.mp4",
                "processing_status": "analyzed",
                "sha256": "abc",
            },
            {
                "evidence_id": "cam-b",
                "original_filename": "b.mp4",
                "processing_status": "analyzed",
                "sha256": "def",
            },
        ],
        {"events": []},
        [
            {"evidence_id": "cam-a", "track_id": 1, "class_name": "car", "confidence": 0.9},
            {"evidence_id": "cam-b", "track_id": 4, "class_name": "car", "confidence": 0.8},
        ],
        [
            {
                "first": {"evidence_id": "cam-a", "track_id": 1},
                "second": {"evidence_id": "cam-b", "track_id": 4},
                "probability": 0.87,
                "review_status": "confirmed",
            }
        ],
    )
    assert sum(node["type"] == "object" for node in graph["nodes"]) == 2
    assert any(edge["relation"] == "same_object_confirmed" for edge in graph["edges"])
