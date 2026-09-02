"""OpenCV-derived frame quality and motion signals."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import cv2
import numpy as np


class FrameAnalysisError(RuntimeError):
    """Raised when an extracted evidence frame cannot be decoded."""


def analyze_frames(frame_paths: List[Path]) -> List[Dict[str, object]]:
    """Measure brightness, sharpness, and inter-frame motion for each evidence frame."""
    results = []
    previous_gray = None
    for path in frame_paths:
        frame = cv2.imread(str(path))
        if frame is None:
            raise FrameAnalysisError(f"OpenCV could not decode evidence frame: {path}")
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        motion = 0.0
        if previous_gray is not None:
            if previous_gray.shape != gray.shape:
                previous_gray = cv2.resize(previous_gray, (gray.shape[1], gray.shape[0]))
            motion = float(np.mean(cv2.absdiff(gray, previous_gray)) / 255.0)
        results.append(
            {
                "frame_path": str(path.resolve()),
                "width": int(frame.shape[1]),
                "height": int(frame.shape[0]),
                "mean_brightness": round(float(np.mean(gray) / 255.0), 6),
                "sharpness": round(float(cv2.Laplacian(gray, cv2.CV_64F).var()), 6),
                "motion_score": round(motion, 6),
            }
        )
        previous_gray = gray
    return results
