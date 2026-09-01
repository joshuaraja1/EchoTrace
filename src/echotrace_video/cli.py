"""CLI for the Phase 1 single-video processing baseline."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional, Sequence

from .detection import NullDetector, UltralyticsDetector
from .media import MediaProcessingError
from .pipeline import process_video


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Process one EchoTrace video source")
    parser.add_argument("video", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sample-fps", type=float, default=2.0)
    parser.add_argument("--detector", choices=("none", "yolo"), default="none")
    parser.add_argument("--model", default="yolo11n.pt")
    args = parser.parse_args(argv)
    try:
        detector = UltralyticsDetector(args.model) if args.detector == "yolo" else NullDetector()
        manifest = process_video(args.video, args.output, detector, args.sample_fps)
    except (MediaProcessingError, RuntimeError, ValueError) as error:
        parser.error(str(error))
    print(
        f"Processed {manifest['frame_count']} frames; "
        f"found {len(manifest['observations'])} tracked observations"
    )
    print(f"Analysis: {args.output / 'analysis.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

