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
    client = TestClient(
        create_app(tmp_path / "data", detector_factory=MovingCarDetector, require_auth=False)
    )

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

    timeline = client.get(f"/investigations/{investigation_id}/timeline").json()["events"]
    objects = client.get(f"/investigations/{investigation_id}/objects").json()
    assert timeline[0]["event_type"] == "object_enters_scene"
    assert timeline[0]["global_timestamp_seconds"] == 2.75
    assert timeline[0]["evidence"][0]["frame_path"]
    assert len(objects) == 2
    assert objects[0]["class_name"] == "car"

    summary = client.get(f"/investigations/{investigation_id}/summary").json()
    assert summary["citations"]
    assert summary["provider"] == "local_evidence_rules"
    answer = client.post(
        f"/investigations/{investigation_id}/ask",
        json={"question": "When did the car enter the scene?"},
    ).json()
    assert answer["citations"]
    graph = client.get(f"/investigations/{investigation_id}/graph").json()
    assert any(edge["relation"] == "supported_by" for edge in graph["edges"])


def test_processes_text_evidence_and_rejects_unknown_types(tmp_path: Path):
    client = TestClient(
        create_app(tmp_path / "data", detector_factory=MovingCarDetector, require_auth=False)
    )
    investigation = client.post(
        "/investigations",
        json={
            "title": "Test",
            "incident_type": "other",
            "incident_date": "2026-09-01",
            "location": "Lab",
        },
    ).json()
    text_response = client.post(
        f"/investigations/{investigation['investigation_id']}/evidence",
        files={"file": ("notes.txt", b"Witness observed a red vehicle.", "text/plain")},
    )
    assert text_response.status_code == 201
    assert client.post(
        f"/investigations/{investigation['investigation_id']}/process"
    ).json()["processed"] == 1
    answer = client.post(
        f"/investigations/{investigation['investigation_id']}/ask",
        json={"question": "What did the witness observe about the red vehicle?"},
    ).json()
    assert "red vehicle" in answer["answer"]
    assert answer["citations"][0]["evidence_id"] == text_response.json()["evidence_id"]
    response = client.post(
        f"/investigations/{investigation['investigation_id']}/evidence",
        files={"file": ("malware.exe", b"unsupported", "application/octet-stream")},
    )
    assert response.status_code == 415


def test_automatic_synchronization_is_persisted(tmp_path: Path):
    source = tmp_path / "shared.mp4"
    create_test_video(source)
    client = TestClient(
        create_app(tmp_path / "data", detector_factory=MovingCarDetector, require_auth=False)
    )
    investigation_id = client.post(
        "/investigations",
        json={
            "title": "Two Camera Test",
            "incident_type": "vehicle collision",
            "incident_date": "2026-09-02",
            "location": "Lab",
        },
    ).json()["investigation_id"]
    evidence_ids = []
    for filename in ("camera-a.mp4", "camera-b.mp4"):
        with source.open("rb") as video:
            response = client.post(
                f"/investigations/{investigation_id}/evidence",
                files={"file": (filename, video, "video/mp4")},
            )
        evidence_ids.append(response.json()["evidence_id"])
    assert client.post(f"/investigations/{investigation_id}/process").status_code == 200

    response = client.post(
        f"/investigations/{investigation_id}/synchronize",
        json={"reference_evidence_id": evidence_ids[0], "max_offset_seconds": 5},
    )
    assert response.status_code == 200
    assert response.json()["results"][1]["offset_seconds"] == 0
    persisted = client.get(f"/investigations/{investigation_id}/synchronization").json()
    assert persisted[1]["details"]["signals"][0]["method"] == "audio_gcc_phat"
    assert persisted[1]["confidence"] >= 0.5
    matches = client.get(f"/investigations/{investigation_id}/objects/matches").json()
    assert matches[0]["review_status"] == "needs_review"
    reviewed = client.patch(
        f"/investigations/{investigation_id}/objects/matches/{matches[0]['match_id']}",
        json={"decision": "confirmed", "note": "Same controlled vehicle"},
    )
    assert reviewed.status_code == 200
    assert client.get(
        f"/investigations/{investigation_id}/objects/matches"
    ).json()[0]["review_status"] == "confirmed"


def test_authentication_and_investigation_ownership(tmp_path: Path):
    client = TestClient(create_app(tmp_path / "data"))
    assert client.get("/investigations").status_code == 401
    registration = client.post(
        "/auth/register",
        json={
            "name": "Fleet Investigator",
            "email": "investigator@example.com",
            "password": "correct-horse-battery-staple",
        },
    )
    assert registration.status_code == 201
    token = registration.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post(
        "/investigations",
        headers=headers,
        json={
            "title": "Authenticated Test",
            "incident_type": "other",
            "incident_date": "2026-09-02",
            "location": "Lab",
        },
    )
    assert created.status_code == 201
    assert client.get("/investigations", headers=headers).json()[0]["title"] == "Authenticated Test"
    login = client.post(
        "/auth/login",
        json={"email": "investigator@example.com", "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200
    assert login.json()["access_token"]
