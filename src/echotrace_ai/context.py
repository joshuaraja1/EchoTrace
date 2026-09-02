"""Create a compact, citation-addressable evidence context."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Sequence


def build_evidence_context(
    investigation: Dict[str, object],
    evidence_items: Sequence[Dict[str, object]],
    timeline: Dict[str, object],
) -> Dict[str, object]:
    sources = []
    for evidence in evidence_items:
        source = {
            "evidence_id": evidence["evidence_id"],
            "filename": evidence["original_filename"],
            "media_type": evidence["media_type"],
            "sha256": evidence["sha256"],
            "effective_offset_seconds": evidence["effective_offset"],
            "metadata": evidence.get("metadata"),
        }
        analysis_path = evidence.get("analysis_path")
        if analysis_path and Path(str(analysis_path)).is_file():
            analysis = json.loads(Path(str(analysis_path)).read_text(encoding="utf-8"))
            if "extracted_text" in analysis:
                source["extracted_text"] = analysis["extracted_text"]
        sources.append(source)
    return {
        "investigation": {
            key: investigation.get(key)
            for key in (
                "investigation_id",
                "title",
                "incident_type",
                "incident_date",
                "approximate_time",
                "location",
                "description",
            )
        },
        "sources": sources,
        "timeline": timeline,
        "policy": {
            "no_fault_or_liability": True,
            "uncertainty_required": True,
            "citations_required": True,
        },
    }


def filter_context_to_events(
    context: Dict[str, object], event_ids: Sequence[str]
) -> Dict[str, object]:
    selected = set(event_ids)
    timeline = dict(context["timeline"])
    timeline["events"] = [
        event for event in timeline.get("events", []) if str(event["event_id"]) in selected
    ]
    timeline["event_count"] = len(timeline["events"])
    return {**context, "timeline": timeline}
