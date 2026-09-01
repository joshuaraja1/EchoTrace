"""Command-line interface for the Phase 0 synchronization spike."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Optional

from .audio import AudioExtractionError
from .synchronizer import synchronize_files


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="echotrace-sync",
        description="Estimate temporal offsets between recordings of the same incident.",
    )
    parser.add_argument("files", nargs="+", type=Path, help="Video or audio files to synchronize")
    parser.add_argument("--reference", type=Path, help="Reference file (defaults to first input)")
    parser.add_argument("--output", type=Path, help="Write JSON to this path instead of stdout")
    parser.add_argument("--sample-rate", type=int, default=8_000)
    parser.add_argument("--max-offset", type=float, help="Maximum absolute offset in seconds")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    reference = args.reference or args.files[0]
    try:
        manifest = synchronize_files(
            args.files,
            reference,
            sample_rate=args.sample_rate,
            max_offset_seconds=args.max_offset,
        )
    except (AudioExtractionError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    rendered = json.dumps(manifest, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(f"Wrote synchronization manifest to {args.output}")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
