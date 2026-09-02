"""Evidence-grounded local reasoning with an optional Microsoft Foundry adapter."""

from __future__ import annotations

import json
import os
import re
from typing import Dict, List, Protocol


class EvidenceReasoner(Protocol):
    provider: str

    def summarize(self, context: Dict[str, object]) -> Dict[str, object]:
        ...

    def answer(self, question: str, context: Dict[str, object]) -> Dict[str, object]:
        ...


def _events(context: Dict[str, object]) -> List[Dict[str, object]]:
    timeline = context.get("timeline", {})
    return list(timeline.get("events", [])) if isinstance(timeline, dict) else []


def _citation(event: Dict[str, object]) -> Dict[str, object]:
    evidence = list(event.get("evidence", []))
    return {
        "event_id": event["event_id"],
        "event_type": event["event_type"],
        "global_timestamp_seconds": event["global_timestamp_seconds"],
        "evidence": evidence,
    }


def _source_matches(question_tokens: set, context: Dict[str, object]) -> List[Dict[str, object]]:
    matches = []
    for source in context.get("sources", []):
        text = str(source.get("extracted_text", ""))
        score = len(question_tokens.intersection(set(re.findall(r"[a-z0-9]+", text.lower()))))
        if score:
            matches.append(
                {
                    "score": score,
                    "source": source,
                    "snippet": " ".join(text.split())[:280],
                }
            )
    return sorted(matches, key=lambda item: item["score"], reverse=True)[:3]


class LocalEvidenceReasoner:
    provider = "local_evidence_rules"

    def summarize(self, context: Dict[str, object]) -> Dict[str, object]:
        events = _events(context)
        if not events:
            return {
                "summary": "No analyzed timeline events are available yet.",
                "citations": [],
                "confidence": 0.0,
                "warning": "Process evidence before requesting a reconstruction summary.",
            }
        selected = events[:5]
        descriptions = [
            f"At estimated T+{float(event['global_timestamp_seconds']):.2f}s, "
            f"{str(event['description']).rstrip('.').lower()}."
            for event in selected
        ]
        return {
            "summary": " ".join(descriptions),
            "citations": [_citation(event) for event in selected],
            "confidence": round(min(float(event["confidence"]) for event in selected), 4),
            "warning": "This reconstruction describes detected evidence and does not assign fault.",
        }

    def answer(self, question: str, context: Dict[str, object]) -> Dict[str, object]:
        events = _events(context)
        lowered = question.lower()
        keywords = {
            token
            for token in re.findall(r"[a-z0-9]+", lowered)
            if len(token) > 2 and token not in {"what", "when", "which", "before", "after", "does"}
        }
        scored_events = [
            (
                len(
                    keywords.intersection(
                        set(re.findall(r"[a-z0-9]+", json.dumps(event).lower()))
                    )
                ),
                event,
            )
            for event in events
        ]
        relevant = [
            event for score, event in sorted(scored_events, reverse=True, key=lambda item: item[0]) if score
        ][:3]
        source_matches = _source_matches(keywords, context)
        if not relevant and not source_matches and events:
            relevant = events[:3]
        if not relevant and not source_matches:
            return {
                "answer": "The available evidence does not contain analyzed events for this question.",
                "citations": [],
                "confidence": 0.0,
                "warning": "Insufficient evidence",
            }
        event_text = " ".join(
            f"At estimated T+{float(event['global_timestamp_seconds']):.2f}s, "
            f"{str(event['description']).rstrip('.').lower()}."
            for event in relevant
        )
        source_text = " ".join(
            f"Source {match['source']['filename']} contains: {match['snippet']}."
            for match in source_matches
        )
        citations = [_citation(event) for event in relevant]
        citations.extend(
            {
                "evidence_id": match["source"]["evidence_id"],
                "source": match["source"]["filename"],
                "type": "extracted_text",
            }
            for match in source_matches
        )
        confidences = [float(event["confidence"]) for event in relevant]
        if source_matches:
            confidences.append(0.7)
        return {
            "answer": f"Based on the analyzed evidence: {event_text} {source_text}".strip(),
            "citations": citations,
            "confidence": round(min(confidences), 4),
            "warning": "This answer is limited to the cited evidence and does not assign fault.",
        }


class AzureFoundryReasoner:
    provider = "microsoft_foundry"

    def __init__(self, endpoint: str, model: str) -> None:
        try:
            from azure.ai.projects import AIProjectClient
            from azure.identity import DefaultAzureCredential
        except ImportError as error:
            raise RuntimeError("Install Azure support with: pip install -e '.[azure]'") from error
        project = AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential())
        self.client = project.get_openai_client()
        self.model = model

    def _run(self, task: str, context: Dict[str, object]) -> Dict[str, object]:
        allowed_ids = {str(event["event_id"]) for event in _events(context)}
        prompt = (
            "You are EchoTrace, an evidence reconstruction assistant. Never assign fault or "
            "liability. Use only the supplied JSON evidence. Return JSON with text, citations "
            "(an array of event_id strings), confidence from 0 to 1, and warning. If evidence is "
            "insufficient, say so.\nTASK:\n"
            + task
            + "\nEVIDENCE:\n"
            + json.dumps(context, separators=(",", ":"))
        )
        response = self.client.responses.create(model=self.model, input=prompt)
        try:
            parsed = json.loads(response.output_text)
        except (AttributeError, json.JSONDecodeError) as error:
            raise RuntimeError("Foundry response was not valid grounded JSON") from error
        citations = {str(value) for value in parsed.get("citations", [])}
        if not citations.issubset(allowed_ids):
            raise RuntimeError("Foundry response cited evidence outside this investigation")
        citation_records = [
            _citation(event) for event in _events(context) if str(event["event_id"]) in citations
        ]
        return {
            "text": str(parsed.get("text", "")),
            "citations": citation_records,
            "confidence": float(parsed.get("confidence", 0)),
            "warning": parsed.get("warning"),
        }

    def summarize(self, context: Dict[str, object]) -> Dict[str, object]:
        result = self._run("Summarize the apparent event sequence.", context)
        result["summary"] = result.pop("text")
        return result

    def answer(self, question: str, context: Dict[str, object]) -> Dict[str, object]:
        result = self._run(f"Answer this investigator question: {question}", context)
        result["answer"] = result.pop("text")
        return result


def create_reasoner() -> EvidenceReasoner:
    if os.environ.get("ECHOTRACE_REASONER", "local").lower() != "azure":
        return LocalEvidenceReasoner()
    endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
    model = os.environ.get("AZURE_AI_MODEL")
    if not endpoint or not model:
        raise RuntimeError(
            "Azure reasoning requires AZURE_AI_PROJECT_ENDPOINT and AZURE_AI_MODEL"
        )
    return AzureFoundryReasoner(endpoint, model)
