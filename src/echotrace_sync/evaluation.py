"""Evaluate synchronization manifests against measured ground truth."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Optional, Sequence

import numpy as np


def evaluate_manifest(
    manifest: Dict[str, object], ground_truth: Dict[str, float], threshold_seconds: float = 0.5
) -> Dict[str, object]:
    sources = manifest.get("sources")
    if not isinstance(sources, dict):
        raise TypeError("manifest must contain a sources object")
    if threshold_seconds <= 0:
        raise ValueError("threshold_seconds must be positive")

    rows = []
    for source, expected in ground_truth.items():
        prediction = sources.get(source)
        if prediction is None:
            matches = [value for key, value in sources.items() if Path(key).name == Path(source).name]
            if len(matches) != 1:
                raise ValueError(f"No unique prediction found for ground-truth source: {source}")
            prediction = matches[0]
        if not isinstance(prediction, dict) or "offset_seconds" not in prediction:
            raise ValueError(f"Invalid prediction for source: {source}")
        estimated = float(prediction["offset_seconds"])
        error = abs(estimated - float(expected))
        rows.append(
            {
                "source": source,
                "expected_offset_seconds": float(expected),
                "estimated_offset_seconds": estimated,
                "absolute_error_seconds": round(error, 6),
                "within_threshold": error <= threshold_seconds,
            }
        )

    if not rows:
        raise ValueError("ground truth must contain at least one source")
    errors = np.array([row["absolute_error_seconds"] for row in rows], dtype=float)
    median = float(np.median(errors))
    return {
        "threshold_seconds": threshold_seconds,
        "sample_count": len(rows),
        "median_absolute_error_seconds": round(median, 6),
        "p95_absolute_error_seconds": round(float(np.percentile(errors, 95)), 6),
        "failure_rate": round(float(np.mean(errors > threshold_seconds)), 6),
        "phase_0_gate_passed": median <= threshold_seconds,
        "results": rows,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate EchoTrace synchronization accuracy")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("ground_truth", type=Path)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    ground_truth = json.loads(args.ground_truth.read_text(encoding="utf-8"))
    try:
        report = evaluate_manifest(manifest, ground_truth, args.threshold)
    except (TypeError, ValueError) as error:
        parser.error(str(error))
    rendered = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(f"Wrote evaluation report to {args.output}")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
