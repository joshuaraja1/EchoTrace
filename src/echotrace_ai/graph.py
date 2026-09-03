"""Inspectable evidence graph assembled from backend artifacts."""

from __future__ import annotations

from typing import Dict, Optional, Sequence


def build_evidence_graph(
    investigation: Dict[str, object],
    evidence_items: Sequence[Dict[str, object]],
    timeline: Dict[str, object],
    observations: Optional[Sequence[Dict[str, object]]] = None,
    matches: Optional[Sequence[Dict[str, object]]] = None,
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
    seen_tracks = set()
    for observation in observations or []:
        evidence_id = str(observation["evidence_id"])
        track_id = int(observation["track_id"])
        track_key = (evidence_id, track_id)
        if track_key in seen_tracks:
            continue
        seen_tracks.add(track_key)
        object_node = f"object:{evidence_id}:{track_id}"
        label = observation.get("canonical_identity") or (
            f"{str(observation.get('class_name', 'object')).title()} {track_id}"
        )
        nodes.append(
            {
                "id": object_node,
                "type": "object",
                "label": label,
                "class_name": observation.get("class_name"),
                "confidence": observation.get("confidence"),
            }
        )
        edges.append(
            {
                "source": object_node,
                "target": f"evidence:{evidence_id}",
                "relation": "observed_in",
                "confidence": float(observation.get("confidence", 0)),
            }
        )
    for match in matches or []:
        first, second = match["first"], match["second"]
        edges.append(
            {
                "source": f"object:{first['evidence_id']}:{first['track_id']}",
                "target": f"object:{second['evidence_id']}:{second['track_id']}",
                "relation": (
                    "same_object_confirmed"
                    if match.get("review_status") == "confirmed"
                    else "possible_same_object"
                ),
                "confidence": float(match["probability"]),
                "review_status": match.get("review_status", "needs_review"),
            }
        )
    return {"nodes": nodes, "edges": edges}
