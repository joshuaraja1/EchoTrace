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
