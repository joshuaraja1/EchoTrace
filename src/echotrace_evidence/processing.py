"""Process supported evidence while keeping source files immutable."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from pypdf import PdfReader

from echotrace_video.detection import Detector
from echotrace_video.events import detect_track_events
from echotrace_video.models import Observation
from echotrace_video.opencv_analysis import analyze_frames
from echotrace_video.pipeline import process_video

VIDEO_EXTENSIONS = {".mp4", ".mov"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
DOCUMENT_EXTENSIONS = {".txt", ".pdf"}
SUPPORTED_EXTENSIONS = VIDEO_EXTENSIONS | IMAGE_EXTENSIONS | DOCUMENT_EXTENSIONS


def _write_manifest(output_dir: Path, manifest: Dict[str, object]) -> Dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "analysis.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def process_image(path: Path, output_dir: Path, detector: Detector) -> Dict[str, object]:
    frame_analysis = analyze_frames([path])
    detections = detector.detect(path)
    observations = [
        Observation(
            0.0,
            str(path.resolve()),
            index,
            detection.class_name,
            detection.confidence,
            detection.box,
        )
        for index, detection in enumerate(detections, start=1)
    ]
    return _write_manifest(
        output_dir,
        {
            "schema_version": "1.0",
            "evidence_type": "image",
            "metadata": {
                "path": str(path.resolve()),
                "width": frame_analysis[0]["width"],
                "height": frame_analysis[0]["height"],
            },
            "frame_analysis": frame_analysis,
            "observations": [item.to_dict() for item in observations],
            "timeline": [item.to_dict() for item in detect_track_events(observations)],
        },
    )


def process_document(path: Path, output_dir: Path) -> Dict[str, object]:
    if path.suffix.lower() == ".pdf":
        text = "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
    else:
        text = path.read_text(encoding="utf-8", errors="replace")
    return _write_manifest(
        output_dir,
        {
            "schema_version": "1.0",
            "evidence_type": "document",
            "metadata": {"path": str(path.resolve()), "character_count": len(text)},
            "extracted_text": text,
            "observations": [],
            "timeline": [],
        },
    )


def process_evidence(path: Path, output_dir: Path, detector: Detector) -> Dict[str, object]:
    extension = path.suffix.lower()
    if extension in VIDEO_EXTENSIONS:
        return process_video(path, output_dir, detector)
    if extension in IMAGE_EXTENSIONS:
        return process_image(path, output_dir, detector)
    if extension in DOCUMENT_EXTENSIONS:
        return process_document(path, output_dir)
    raise ValueError(f"Unsupported evidence type: {extension}")
