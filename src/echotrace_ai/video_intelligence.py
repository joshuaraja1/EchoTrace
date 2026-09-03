"""Optional Azure AI Video Indexer enrichment without facial identity processing."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Dict, Protocol

import httpx


class VideoIntelligenceError(RuntimeError):
    """Raised when optional cloud indexing cannot produce a usable result."""


class VideoIntelligence(Protocol):
    provider: str

    def enrich(self, path: Path) -> Dict[str, object]: ...


class LocalVideoIntelligence:
    provider = "local_only"

    def enrich(self, path: Path) -> Dict[str, object]:
        return {}


class AzureVideoIndexer:
    """Index a private video and retain only MVP-safe, evidence-useful insights."""

    provider = "azure_ai_video_indexer"

    def __init__(
        self,
        subscription_id: str,
        resource_group: str,
        account_name: str,
        account_id: str,
        location: str,
        poll_seconds: float = 5.0,
        timeout_seconds: float = 900.0,
    ) -> None:
        try:
            from azure.identity import DefaultAzureCredential
        except ImportError as error:
            raise RuntimeError("Install Azure support with: pip install -e '.[azure]'") from error
        self.credential = DefaultAzureCredential()
        self.subscription_id = subscription_id
        self.resource_group = resource_group
        self.account_name = account_name
        self.account_id = account_id
        self.location = location
        self.poll_seconds = poll_seconds
        self.timeout_seconds = timeout_seconds

    def _account_token(self, permission: str) -> str:
        arm_token = self.credential.get_token("https://management.azure.com/.default").token
        endpoint = (
            "https://management.azure.com/subscriptions/"
            f"{self.subscription_id}/resourceGroups/{self.resource_group}/providers/"
            f"Microsoft.VideoIndexer/accounts/{self.account_name}/generateAccessToken"
        )
        response = httpx.post(
            endpoint,
            params={"api-version": "2025-04-01"},
            headers={"Authorization": f"Bearer {arm_token}"},
            json={"permissionType": permission, "scope": "Account"},
            timeout=30,
        )
        response.raise_for_status()
        return str(response.json()["accessToken"])

    def enrich(self, path: Path) -> Dict[str, object]:
        token = self._account_token("Contributor")
        base = f"https://api.videoindexer.ai/{self.location}/Accounts/{self.account_id}"
        with path.open("rb") as source:
            response = httpx.post(
                f"{base}/Videos",
                params={
                    "accessToken": token,
                    "name": path.stem,
                    "privacy": "Private",
                    "streamingPreset": "NoStreaming",
                    "indexingPreset": "Default",
                    "excludedAI": "Faces,ObservedPeople,Emotions",
                },
                files={"file": (path.name, source, "application/octet-stream")},
                timeout=None,
            )
        response.raise_for_status()
        video_id = str(response.json()["id"])
        deadline = time.monotonic() + self.timeout_seconds
        while time.monotonic() < deadline:
            index_response = httpx.get(
                f"{base}/Videos/{video_id}/Index",
                params={"accessToken": token, "language": "English"},
                timeout=30,
            )
            index_response.raise_for_status()
            payload = index_response.json()
            state = str(payload.get("state", ""))
            if state == "Processed":
                return self._safe_insights(payload, video_id)
            if state in {"Failed", "Error"}:
                raise VideoIntelligenceError(f"Azure Video Indexer finished with state: {state}")
            time.sleep(self.poll_seconds)
        raise VideoIntelligenceError("Azure Video Indexer did not finish before the timeout")

    @staticmethod
    def _safe_insights(payload: Dict[str, object], video_id: str) -> Dict[str, object]:
        videos = payload.get("videos") or []
        insights = videos[0].get("insights", {}) if videos else {}
        transcript = [
            {"text": item.get("text"), "confidence": item.get("confidence"), "instances": item.get("instances", [])}
            for item in insights.get("transcript", [])
        ]
        ocr = [
            {"text": item.get("text"), "confidence": item.get("confidence"), "instances": item.get("instances", [])}
            for item in insights.get("ocr", [])
        ]
        return {
            "provider": "azure_ai_video_indexer",
            "video_id": video_id,
            "transcript": transcript,
            "ocr": ocr,
            "labels": insights.get("labels", []),
            "keywords": insights.get("keywords", []),
            "scenes": insights.get("scenes", []),
            "shots": insights.get("shots", []),
            "privacy": "Private",
            "excluded_insights": ["faces", "recognized_people"],
        }


def create_video_intelligence() -> VideoIntelligence:
    if os.environ.get("ECHOTRACE_VIDEO_INTELLIGENCE", "local").lower() != "azure":
        return LocalVideoIntelligence()
    variables = {
        "subscription_id": os.environ.get("AZURE_VIDEO_INDEXER_SUBSCRIPTION_ID"),
        "resource_group": os.environ.get("AZURE_VIDEO_INDEXER_RESOURCE_GROUP"),
        "account_name": os.environ.get("AZURE_VIDEO_INDEXER_ACCOUNT_NAME"),
        "account_id": os.environ.get("AZURE_VIDEO_INDEXER_ACCOUNT_ID"),
        "location": os.environ.get("AZURE_VIDEO_INDEXER_LOCATION"),
    }
    missing = [name for name, value in variables.items() if not value]
    if missing:
        raise RuntimeError(f"Azure Video Indexer is missing configuration: {', '.join(missing)}")
    return AzureVideoIndexer(**variables)  # type: ignore[arg-type]
