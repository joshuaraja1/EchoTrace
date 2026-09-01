"""Serializable domain models for video observations and events."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class VideoMetadata:
    path: str
    duration_seconds: float
    width: int
    height: int
    fps: float
    has_audio: bool

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class Detection:
    class_name: str
    confidence: float
    box: Tuple[float, float, float, float]

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class Observation:
    timestamp_seconds: float
    frame_path: str
    track_id: int
    class_name: str
    confidence: float
    box: Tuple[float, float, float, float]

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class TimelineEvent:
    event_type: str
    timestamp_seconds: float
    track_id: int
    description: str
    confidence: float
    frame_path: Optional[str]

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


Manifest = Dict[str, object]
ObservationList = List[Observation]

