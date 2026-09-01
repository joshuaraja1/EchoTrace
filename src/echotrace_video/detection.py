"""Detector adapters. Heavy vision models are optional and loaded lazily."""

from __future__ import annotations

from pathlib import Path
from typing import List, Protocol

from .models import Detection

SUPPORTED_CLASSES = {"car", "truck", "motorcycle", "bicycle", "person"}


class Detector(Protocol):
    def detect(self, frame_path: Path) -> List[Detection]:
        ...


class NullDetector:
    """Allows metadata/frame extraction without installing a model."""

    def detect(self, frame_path: Path) -> List[Detection]:
        return []


class UltralyticsDetector:
    def __init__(self, model_name: str = "yolo11n.pt", confidence: float = 0.35) -> None:
        try:
            from ultralytics import YOLO
        except ImportError as error:
            raise RuntimeError("Install EchoTrace with the vision extra: pip install -e '.[vision]'") from error
        self.model = YOLO(model_name)
        self.confidence = confidence

    def detect(self, frame_path: Path) -> List[Detection]:
        result = self.model.predict(str(frame_path), conf=self.confidence, verbose=False)[0]
        detections = []
        for box in result.boxes:
            class_name = result.names[int(box.cls.item())]
            if class_name not in SUPPORTED_CLASSES:
                continue
            coordinates = tuple(float(value) for value in box.xyxy[0].tolist())
            detections.append(Detection(class_name, float(box.conf.item()), coordinates))
        return detections

