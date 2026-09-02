"""Local retrieval and optional Azure AI Search integration."""

from __future__ import annotations

import os
import re
from typing import Dict, List, Protocol


class EvidenceSearch(Protocol):
    provider: str

    def index_context(self, context: Dict[str, object]) -> None:
        ...

    def search(self, question: str, context: Dict[str, object], limit: int = 8) -> List[str]:
        ...


class LocalEvidenceSearch:
    provider = "local_keyword"

    def index_context(self, context: Dict[str, object]) -> None:
        return None

    def search(self, question: str, context: Dict[str, object], limit: int = 8) -> List[str]:
        tokens = set(re.findall(r"[a-z0-9]+", question.lower()))
        events = context.get("timeline", {}).get("events", [])
        ranked = sorted(
            events,
            key=lambda event: len(
                tokens.intersection(set(re.findall(r"[a-z0-9]+", str(event).lower())))
            ),
            reverse=True,
        )
        return [str(event["event_id"]) for event in ranked[:limit]]


class AzureEvidenceSearch:
    provider = "azure_ai_search"

    def __init__(self, endpoint: str, index_name: str) -> None:
        try:
            from azure.identity import DefaultAzureCredential
            from azure.search.documents import SearchClient
        except ImportError as error:
            raise RuntimeError("Install Azure support with: pip install -e '.[azure]'") from error
        self.client = SearchClient(endpoint, index_name, DefaultAzureCredential())

    def index_context(self, context: Dict[str, object]) -> None:
        investigation_id = str(context["investigation"]["investigation_id"])
        documents = []
        for event in context.get("timeline", {}).get("events", []):
            documents.append(
                {
                    "id": str(event["event_id"]),
                    "investigation_id": investigation_id,
                    "event_id": str(event["event_id"]),
                    "content": str(event["description"]),
                    "event_type": str(event["event_type"]),
                    "timestamp_seconds": float(event["global_timestamp_seconds"]),
                }
            )
        if documents:
            self.client.merge_or_upload_documents(documents)

    def search(self, question: str, context: Dict[str, object], limit: int = 8) -> List[str]:
        investigation_id = str(context["investigation"]["investigation_id"]).replace("'", "''")
        results = self.client.search(
            search_text=question,
            filter=f"investigation_id eq '{investigation_id}'",
            select=["event_id"],
            top=limit,
        )
        return [str(result["event_id"]) for result in results]


def create_search() -> EvidenceSearch:
    if os.environ.get("ECHOTRACE_SEARCH", "local").lower() != "azure":
        return LocalEvidenceSearch()
    endpoint = os.environ.get("AZURE_SEARCH_ENDPOINT")
    index_name = os.environ.get("AZURE_SEARCH_INDEX")
    if not endpoint or not index_name:
        raise RuntimeError("Azure search requires AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_INDEX")
    return AzureEvidenceSearch(endpoint, index_name)
