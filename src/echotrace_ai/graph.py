"""Inspectable evidence graph assembled from backend artifacts."""

from __future__ import annotations

from typing import Dict, Sequence


def build_evidence_graph(
    investigation: Dict[str, object],
    evidence_items: Sequence[Dict[str, object]],
    timeline: Dict[str, object],
) -> Dict[str, object]:
    investigation_id = str(investigation["investigation_id"])
    nodes = [
        {
            "id": f"investigation:{investigation_id}",
            "type": "investigation",
            "label": investigation["title"],
        }
    ]
    edges = []
    for evidence in evidence_items:
        evidence_node = f"evidence:{evidence['evidence_id']}"
        nodes.append(
            {
                "id": evidence_node,
                "type": "evidence",
                "label": evidence["original_filename"],
                "status": evidence["processing_status"],
                "sha256": evidence["sha256"],
            }
        )
        edges.append(
            {
                "source": f"investigation:{investigation_id}",
                "target": evidence_node,
                "relation": "contains",
                "confidence": 1.0,
            }
        )
    for event in timeline.get("events", []):
        event_node = f"event:{event['event_id']}"
        nodes.append(
            {
                "id": event_node,
                "type": "event",
                "label": event["description"],
                "timestamp_seconds": event["global_timestamp_seconds"],
                "confidence": event["confidence"],
            }
        )
        for citation in event["evidence"]:
            edges.append(
                {
                    "source": event_node,
                    "target": f"evidence:{citation['evidence_id']}",
                    "relation": "supported_by",
                    "confidence": citation["confidence"],
                }
            )
    return {"nodes": nodes, "edges": edges}
