"""Orchestrate Phase 1 metadata, frames, detections, tracks, and timeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .detection import Detector, NullDetector
from .events import detect_track_events
from .media import extract_frames, probe_video
from .models import Manifest, Observation
from .opencv_analysis import analyze_frames
from .tracking import IoUTracker


def process_video(
    video_path: Path,
    output_dir: Path,
    detector: Optional[Detector] = None,
    sample_fps: float = 2.0,
) -> Manifest:
    detector = detector or NullDetector()
    metadata = probe_video(video_path)
    frames_dir = output_dir / "frames"
    frames = extract_frames(video_path, frames_dir, sample_fps)
    frame_analysis = analyze_frames(frames)
    tracker = IoUTracker()
    observations = []
    for index, frame in enumerate(frames):
        timestamp = index / sample_fps
        for track_id, detection in tracker.update(detector.detect(frame)):
            observations.append(
                Observation(
                    timestamp,
                    str(frame.resolve()),
                    track_id,
                    detection.class_name,
                    detection.confidence,
                    detection.box,
                )
            )
    events = detect_track_events(observations)
    manifest: Manifest = {
        "schema_version": "1.0",
        "metadata": metadata.to_dict(),
        "sample_fps": sample_fps,
        "frame_count": len(frames),
        "frame_analysis": frame_analysis,
        "observations": [item.to_dict() for item in observations],
        "timeline": [item.to_dict() for item in events],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "analysis.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest
