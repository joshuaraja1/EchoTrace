"""Evaluate a reconstruction against human-labeled ground truth."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple


def _safe_ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _classification_counts(predicted: Iterable[str], actual: Iterable[str]) -> Dict[str, float]:
    predicted_counts, actual_counts = Counter(predicted), Counter(actual)
    true_positive = sum((predicted_counts & actual_counts).values())
    predicted_total, actual_total = sum(predicted_counts.values()), sum(actual_counts.values())
    precision = _safe_ratio(true_positive, predicted_total)
    recall = _safe_ratio(true_positive, actual_total)
    f1 = round(2 * precision * recall / (precision + recall), 4) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def _binary_counts(predicted: Sequence[bool], actual: Sequence[bool]) -> Dict[str, float]:
    if len(predicted) != len(actual):
        raise ValueError("Collision prediction and ground-truth arrays must have equal length")
    true_positive = sum(prediction and truth for prediction, truth in zip(predicted, actual))
    false_positive = sum(prediction and not truth for prediction, truth in zip(predicted, actual))
    false_negative = sum(not prediction and truth for prediction, truth in zip(predicted, actual))
    precision = _safe_ratio(true_positive, true_positive + false_positive)
    recall = _safe_ratio(true_positive, true_positive + false_negative)
    f1 = round(2 * precision * recall / (precision + recall), 4) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def _event_errors(
    predicted: Sequence[Dict[str, object]], actual: Sequence[Dict[str, object]]
) -> List[float]:
    remaining = list(predicted)
    errors: List[float] = []
    for expected in actual:
        same_type: List[Tuple[int, Dict[str, object]]] = [
            (index, event)
            for index, event in enumerate(remaining)
            if event.get("event_type") == expected.get("event_type")
        ]
        if not same_type:
            continue
        index, candidate = min(
            same_type,
            key=lambda item: abs(
                float(item[1]["timestamp_seconds"]) - float(expected["timestamp_seconds"])
            ),
        )
        errors.append(abs(float(candidate["timestamp_seconds"]) - float(expected["timestamp_seconds"])))
        remaining.pop(index)
    return errors


def _normalize_match(item: Sequence[str]) -> Tuple[str, str]:
    if len(item) != 2:
        raise ValueError("Each cross-camera match must contain exactly two track identifiers")
    return tuple(sorted((str(item[0]), str(item[1]))))


def evaluate_trial(payload: Dict[str, object]) -> Dict[str, object]:
    """Calculate every quantitative Phase 6 metric represented in a labeled trial JSON."""
    predicted = dict(payload.get("predictions") or {})
    truth = dict(payload.get("ground_truth") or {})

    predicted_offsets = dict(predicted.get("synchronization_offsets") or {})
    true_offsets = dict(truth.get("synchronization_offsets") or {})
    shared_sources = sorted(set(predicted_offsets) & set(true_offsets))
    sync_errors = [abs(float(predicted_offsets[key]) - float(true_offsets[key])) for key in shared_sources]

    predicted_events = list(predicted.get("events") or [])
    true_events = list(truth.get("events") or [])
    event_errors = _event_errors(predicted_events, true_events)

    detection = _classification_counts(
        (str(item) for item in predicted.get("object_classes", [])),
        (str(item) for item in truth.get("object_classes", [])),
    )
    collision = _binary_counts(
        [bool(item) for item in predicted.get("collision_labels", [])],
        [bool(item) for item in truth.get("collision_labels", [])],
    )

    predicted_matches = {_normalize_match(item) for item in predicted.get("matches", [])}
    true_matches = {_normalize_match(item) for item in truth.get("matches", [])}
    correct_matches = len(predicted_matches & true_matches)

    predicted_citations = {
        str(claim): {str(source) for source in sources}
        for claim, sources in dict(predicted.get("citations") or {}).items()
    }
    true_citations = {
        str(claim): {str(source) for source in sources}
        for claim, sources in dict(truth.get("citations") or {}).items()
    }
    citation_total = sum(len(sources) for sources in predicted_citations.values())
    citation_correct = sum(
        len(sources & true_citations.get(claim, set()))
        for claim, sources in predicted_citations.items()
    )

    median_sync = round(statistics.median(sync_errors), 4) if sync_errors else None
    median_event = round(statistics.median(event_errors), 4) if event_errors else None
    return {
        "schema_version": "1.0",
        "sample": {
            "trial_id": payload.get("trial_id"),
            "synchronization_sources": len(shared_sources),
            "ground_truth_events": len(true_events),
            "collision_examples": len(predicted.get("collision_labels", [])),
        },
        "metrics": {
            "median_synchronization_error_seconds": median_sync,
            "median_event_timestamp_error_seconds": median_event,
            "object_detection": detection,
            "collision_detection": collision,
            "cross_camera_matching_accuracy": _safe_ratio(correct_matches, len(true_matches)),
            "evidence_citation_accuracy": _safe_ratio(citation_correct, citation_total),
        },
        "targets": {
            "synchronization_under_0_5_seconds": median_sync is not None and median_sync < 0.5,
            "event_timestamp_under_1_second": median_event is not None and median_event < 1.0,
            "cross_camera_matching_at_least_90_percent": (
                bool(true_matches) and _safe_ratio(correct_matches, len(true_matches)) >= 0.9
            ),
            "citation_accuracy_at_least_95_percent": (
                citation_total > 0 and _safe_ratio(citation_correct, citation_total) >= 0.95
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate an EchoTrace labeled reconstruction trial")
    parser.add_argument("trial", type=Path, help="JSON containing predictions and ground_truth")
    parser.add_argument("--output", type=Path, help="Optional report output path")
    args = parser.parse_args()
    report = evaluate_trial(json.loads(args.trial.read_text(encoding="utf-8")))
    serialized = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    print(serialized, end="")


if __name__ == "__main__":
    main()
