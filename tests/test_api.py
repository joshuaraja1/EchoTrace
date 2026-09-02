import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from echotrace_api.app import create_app
from echotrace_video.models import Detection


class MovingCarDetector:
    def __init__(self):
        self.index = 0

    def detect(self, frame_path: Path):
        self.index += 1
        x = float(self.index * 2)
        return [Detection("car", 0.9, (x, 10, x + 30, 40))]


def create_test_video(path: Path) -> None:
    result = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=duration=1:size=160x120:rate=10",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=600:duration=1:sample_rate=8000",
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-y",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_phase_one_investigation_end_to_end(tmp_path: Path):
    source = tmp_path / "camera-a.mp4"
    create_test_video(source)
    client = TestClient(create_app(tmp_path / "data", detector_factory=MovingCarDetector))

    created = client.post(
        "/investigations",
        json={
            "title": "Controlled Collision 001",
            "incident_type": "vehicle collision",
            "incident_date": "2026-09-01",
            "approximate_time": "14:30:00",
            "location": "Controlled test area",
            "description": "Phase 1 end-to-end verification",
        },
    )
    assert created.status_code == 201
    investigation_id = created.json()["investigation_id"]

    with source.open("rb") as video:
        uploaded = client.post(
            f"/investigations/{investigation_id}/evidence",
            files={"file": ("camera-a.mp4", video, "video/mp4")},
        )
    assert uploaded.status_code == 201
    evidence_id = uploaded.json()["evidence_id"]
    assert uploaded.json()["sha256"]

    processed = client.post(f"/investigations/{investigation_id}/process")
    assert processed.status_code == 200
    assert processed.json()["status"] == "analyzed"
    assert processed.json()["processed"] == 1

    detail = client.get(f"/investigations/{investigation_id}").json()
    assert detail["evidence"][0]["processing_status"] == "analyzed"
    assert detail["evidence"][0]["metadata"]["width"] == 160

    adjusted = client.patch(
        f"/investigations/{investigation_id}/evidence/{evidence_id}/synchronization",
        json={"offset_seconds": 2.75, "note": "Aligned to visible test marker"},
    )
    assert adjusted.status_code == 200
    assert adjusted.json()["effective_offset_seconds"] == 2.75

    synchronization = client.get(
        f"/investigations/{investigation_id}/synchronization"
    ).json()
    assert synchronization[0]["effective_offset_seconds"] == 2.75
    assert synchronization[0]["history"][0]["previous_offset"] == 0
    assert synchronization[0]["history"][0]["note"] == "Aligned to visible test marker"

    timeline = client.get(f"/investigations/{investigation_id}/timeline").json()
    objects = client.get(f"/investigations/{investigation_id}/objects").json()
    assert timeline[0]["event_type"] == "object_enters_scene"
    assert timeline[0]["timestamp_seconds"] == 2.75
    assert timeline[0]["frame_path"]
    assert len(objects) == 2
    assert objects[0]["class_name"] == "car"


def test_rejects_unsupported_evidence_without_writing_it(tmp_path: Path):
    client = TestClient(create_app(tmp_path / "data"))
    investigation = client.post(
        "/investigations",
        json={
            "title": "Test",
            "incident_type": "other",
            "incident_date": "2026-09-01",
            "location": "Lab",
        },
    ).json()
    response = client.post(
        f"/investigations/{investigation['investigation_id']}/evidence",
        files={"file": ("notes.txt", b"not video", "text/plain")},
    )
    assert response.status_code == 415
