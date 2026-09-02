import json
from pathlib import Path

from echotrace_video.matching import match_tracks


def analyzed_evidence(tmp_path: Path, identifier: str, x_offset: float):
    path = tmp_path / f"{identifier}.json"
    observations = [
        {
            "timestamp_seconds": index,
            "track_id": 1,
            "class_name": "car",
            "confidence": 0.9,
            "box": [10 + x_offset + index, 10, 40 + x_offset + index, 30],
        }
        for index in range(3)
    ]
    path.write_text(
        json.dumps(
            {
                "metadata": {"width": 100, "height": 100},
                "observations": observations,
            }
        ),
        encoding="utf-8",
    )
    return {
        "evidence_id": identifier,
        "original_filename": f"{identifier}.mp4",
        "analysis_path": str(path),
        "effective_offset": 0,
    }


def test_cross_camera_match_exposes_signals_and_requires_review(tmp_path: Path):
    matches = match_tracks(
        [analyzed_evidence(tmp_path, "camera-a", 0), analyzed_evidence(tmp_path, "camera-b", 3)]
    )
    assert len(matches) == 1
    assert matches[0]["probability"] > 0.8
    assert matches[0]["signals"]["shape_similarity"] == 1
    assert matches[0]["review_status"] == "needs_review"
