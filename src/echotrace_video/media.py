"""FFprobe metadata and deterministic frame sampling."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import List

from .models import VideoMetadata


class MediaProcessingError(RuntimeError):
    """Raised when FFmpeg/FFprobe cannot process a source."""


def _require(binary: str) -> None:
    if shutil.which(binary) is None:
        raise MediaProcessingError(f"{binary} is required but was not found on PATH")


def probe_video(path: Path) -> VideoMetadata:
    _require("ffprobe")
    path = path.resolve()
    if not path.is_file():
        raise MediaProcessingError(f"Video does not exist: {path}")
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_streams",
        "-show_format",
        "-of",
        "json",
        str(path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise MediaProcessingError(result.stderr.strip() or f"Could not probe {path}")
    payload = json.loads(result.stdout)
    video = next((stream for stream in payload.get("streams", []) if stream["codec_type"] == "video"), None)
    if video is None:
        raise MediaProcessingError(f"No video stream found in {path}")
    rate = video.get("avg_frame_rate", "0/1").split("/")
    fps = float(rate[0]) / float(rate[1]) if float(rate[1]) else 0.0
    duration = float(video.get("duration") or payload.get("format", {}).get("duration") or 0)
    return VideoMetadata(
        path=str(path),
        duration_seconds=duration,
        width=int(video["width"]),
        height=int(video["height"]),
        fps=fps,
        has_audio=any(stream["codec_type"] == "audio" for stream in payload.get("streams", [])),
    )


def extract_frames(path: Path, output_dir: Path, sample_fps: float = 2.0) -> List[Path]:
    _require("ffmpeg")
    if sample_fps <= 0:
        raise ValueError("sample_fps must be positive")
    output_dir.mkdir(parents=True, exist_ok=True)
    pattern = output_dir / "frame_%06d.jpg"
    command = [
        "ffmpeg",
        "-v",
        "error",
        "-i",
        str(path.resolve()),
        "-vf",
        f"fps={sample_fps}",
        "-q:v",
        "2",
        "-y",
        str(pattern),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise MediaProcessingError(result.stderr.strip() or f"Could not extract frames from {path}")
    frames = sorted(output_dir.glob("frame_*.jpg"))
    if not frames:
        raise MediaProcessingError(f"No frames extracted from {path}")
    return frames

