"""Audio decoding and lightweight preprocessing."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import numpy as np


class AudioExtractionError(RuntimeError):
    """Raised when FFmpeg cannot decode a media file."""


def extract_audio(path: Path, sample_rate: int = 8_000) -> np.ndarray:
    """Decode a media file to normalized mono float samples using FFmpeg."""
    if shutil.which("ffmpeg") is None:
        raise AudioExtractionError("FFmpeg is required but was not found on PATH")
    if not path.is_file():
        raise AudioExtractionError(f"Media file does not exist: {path}")

    command = [
        "ffmpeg",
        "-v",
        "error",
        "-i",
        str(path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-f",
        "f32le",
        "pipe:1",
    ]
    result = subprocess.run(command, capture_output=True, check=False)
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise AudioExtractionError(f"Could not extract audio from {path}: {detail}")

    samples = np.frombuffer(result.stdout, dtype=np.float32).astype(np.float64)
    if samples.size < sample_rate // 2:
        raise AudioExtractionError(f"Audio in {path} is shorter than 0.5 seconds")
    return preprocess(samples)


def preprocess(samples: np.ndarray) -> np.ndarray:
    """Remove DC, tame outliers, and normalize without changing timing."""
    values = np.asarray(samples, dtype=np.float64)
    values = values - np.median(values)
    scale = np.percentile(np.abs(values), 99.5)
    if not np.isfinite(scale) or scale < 1e-9:
        raise AudioExtractionError("Audio is silent or has insufficient variation")
    values = np.clip(values / scale, -1.0, 1.0)
    # First difference deemphasizes steady engine hum and highlights shared transients.
    return np.diff(values, prepend=values[0])

