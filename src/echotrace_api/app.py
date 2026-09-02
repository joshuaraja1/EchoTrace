"""FastAPI application for a complete local Phase 1 investigation workflow."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Callable, Dict, List, Optional
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from typing_extensions import Annotated

from echotrace_video.detection import Detector, NullDetector
from echotrace_video.pipeline import process_video

from .database import Database, utc_now
from .schemas import InvestigationCreate, SyncAdjustment

VIDEO_EXTENSIONS = {".mp4", ".mov"}
MAX_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024


def _serialize_request(model: InvestigationCreate) -> Dict[str, object]:
    values = model.model_dump()
    values["incident_date"] = values["incident_date"].isoformat()
    if values["approximate_time"] is not None:
        values["approximate_time"] = values["approximate_time"].isoformat()
    return values


def create_app(
    data_dir: Optional[Path] = None,
    detector_factory: Optional[Callable[[], Detector]] = None,
) -> FastAPI:
    root = Path(data_dir or os.environ.get("ECHOTRACE_DATA_DIR", "data")).resolve()
    uploads = root / "evidence"
    analysis_root = root / "analysis"
    uploads.mkdir(parents=True, exist_ok=True)
    analysis_root.mkdir(parents=True, exist_ok=True)
    database = Database(root / "echotrace.db")
    detector_factory = detector_factory or NullDetector

    app = FastAPI(
        title="EchoTrace Phase 1 API",
        version="0.1.0",
        description=(
            "Local investigation and evidence-processing API. EchoTrace reconstructs evidence; "
            "it does not determine fault or liability."
        ),
    )
    app.state.database = database
    app.state.data_dir = root

    def require_investigation(identifier: str) -> Dict[str, object]:
        investigation = database.get_investigation(identifier)
        if investigation is None:
            raise HTTPException(status_code=404, detail="Investigation not found")
        return investigation

    @app.get("/health")
    def health() -> Dict[str, str]:
        return {"status": "ok", "phase": "1"}

    @app.post("/investigations", status_code=status.HTTP_201_CREATED)
    def create_investigation(payload: InvestigationCreate) -> Dict[str, object]:
        return database.create_investigation(_serialize_request(payload))

    @app.get("/investigations")
    def list_investigations() -> List[Dict[str, object]]:
        return database.list_investigations()

    @app.get("/investigations/{investigation_id}")
    def get_investigation(investigation_id: str) -> Dict[str, object]:
        investigation = require_investigation(investigation_id)
        investigation["evidence"] = database.list_evidence(investigation_id)
        return investigation

    @app.delete("/investigations/{investigation_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_investigation(investigation_id: str) -> JSONResponse:
        require_investigation(investigation_id)
        database.delete_investigation(investigation_id)
        return JSONResponse(status_code=204, content=None)

    @app.post(
        "/investigations/{investigation_id}/evidence", status_code=status.HTTP_201_CREATED
    )
    async def upload_evidence(
        investigation_id: str, file: Annotated[UploadFile, File()]
    ) -> Dict[str, object]:
        require_investigation(investigation_id)
        filename = Path(file.filename or "").name
        extension = Path(filename).suffix.lower()
        if extension not in VIDEO_EXTENSIONS:
            raise HTTPException(
                status_code=415,
                detail="Phase 1 accepts video evidence in MP4 or MOV format",
            )
        identifier = str(uuid4())
        target_dir = uploads / investigation_id / identifier
        target_dir.mkdir(parents=True, exist_ok=False)
        target = target_dir / f"original{extension}"
        digest = hashlib.sha256()
        total = 0
        try:
            with target.open("xb") as destination:
                while chunk := await file.read(1024 * 1024):
                    total += len(chunk)
                    if total > MAX_UPLOAD_BYTES:
                        raise HTTPException(status_code=413, detail="Evidence exceeds 2 GB limit")
                    digest.update(chunk)
                    destination.write(chunk)
        except Exception:
            target.unlink(missing_ok=True)
            target_dir.rmdir()
            raise
        finally:
            await file.close()
        values = {
            "evidence_id": identifier,
            "investigation_id": investigation_id,
            "original_filename": filename,
            "media_type": file.content_type or "application/octet-stream",
            "storage_path": str(target),
            "sha256": digest.hexdigest(),
            "processing_status": "uploaded",
            "uploaded_at": utc_now(),
        }
        return database.add_evidence(values)

    @app.get("/investigations/{investigation_id}/evidence")
    def list_evidence(investigation_id: str) -> List[Dict[str, object]]:
        require_investigation(investigation_id)
        return database.list_evidence(investigation_id)

    @app.post("/investigations/{investigation_id}/process")
    def process_investigation(investigation_id: str) -> Dict[str, object]:
        require_investigation(investigation_id)
        evidence_items = database.list_evidence(investigation_id)
        if not evidence_items:
            raise HTTPException(status_code=409, detail="Upload evidence before processing")
        database.set_investigation_status(investigation_id, "processing")
        failures = []
        for evidence in evidence_items:
            evidence_id = str(evidence["evidence_id"])
            database.mark_processing(evidence_id)
            output_dir = analysis_root / investigation_id / evidence_id
            try:
                manifest = process_video(
                    Path(str(evidence["storage_path"])),
                    output_dir,
                    detector_factory(),
                )
                database.mark_analyzed(
                    evidence_id, dict(manifest["metadata"]), output_dir / "analysis.json"
                )
            except (OSError, RuntimeError, ValueError) as error:
                database.mark_failed(evidence_id, str(error))
                failures.append({"evidence_id": evidence_id, "error": str(error)})
        final_status = "needs_review" if failures else "analyzed"
        database.set_investigation_status(investigation_id, final_status)
        return {
            "investigation_id": investigation_id,
            "status": final_status,
            "processed": len(evidence_items) - len(failures),
            "failed": failures,
        }

    @app.get("/investigations/{investigation_id}/status")
    def investigation_status(investigation_id: str) -> Dict[str, object]:
        investigation = require_investigation(investigation_id)
        return {
            "investigation_id": investigation_id,
            "status": investigation["status"],
            "evidence": [
                {
                    "evidence_id": item["evidence_id"],
                    "processing_status": item["processing_status"],
                }
                for item in database.list_evidence(investigation_id)
            ],
        }

    @app.get("/investigations/{investigation_id}/timeline")
    def timeline(investigation_id: str) -> List[Dict[str, object]]:
        require_investigation(investigation_id)
        events = []
        for evidence in database.list_evidence(investigation_id):
            path = evidence.get("analysis_path")
            if not path or not Path(str(path)).is_file():
                continue
            analysis = json.loads(Path(str(path)).read_text(encoding="utf-8"))
            offset = float(evidence["effective_offset"])
            for event in analysis.get("timeline", []):
                event = dict(event)
                event["evidence_id"] = evidence["evidence_id"]
                event["local_timestamp_seconds"] = event["timestamp_seconds"]
                event["timestamp_seconds"] = round(event["timestamp_seconds"] + offset, 6)
                events.append(event)
        return sorted(events, key=lambda event: event["timestamp_seconds"])

    @app.get("/investigations/{investigation_id}/objects")
    def objects(investigation_id: str) -> List[Dict[str, object]]:
        require_investigation(investigation_id)
        observations = []
        for evidence in database.list_evidence(investigation_id):
            path = evidence.get("analysis_path")
            if path and Path(str(path)).is_file():
                analysis = json.loads(Path(str(path)).read_text(encoding="utf-8"))
                observations.extend(
                    {**item, "evidence_id": evidence["evidence_id"]}
                    for item in analysis.get("observations", [])
                )
        return observations

    @app.patch(
        "/investigations/{investigation_id}/evidence/{evidence_id}/synchronization"
    )
    def adjust_synchronization(
        investigation_id: str, evidence_id: str, payload: SyncAdjustment
    ) -> Dict[str, object]:
        require_investigation(investigation_id)
        evidence = database.get_evidence(evidence_id)
        if evidence is None or evidence["investigation_id"] != investigation_id:
            raise HTTPException(status_code=404, detail="Evidence not found")
        adjustment = database.adjust_offset(evidence_id, payload.offset_seconds, payload.note)
        return {
            "evidence_id": evidence_id,
            "effective_offset_seconds": payload.offset_seconds,
            "adjustment": adjustment,
        }

    @app.get("/investigations/{investigation_id}/synchronization")
    def synchronization(investigation_id: str) -> List[Dict[str, object]]:
        require_investigation(investigation_id)
        return [
            {
                "evidence_id": item["evidence_id"],
                "filename": item["original_filename"],
                "estimated_offset_seconds": item["estimated_offset"],
                "manual_offset_seconds": item["manual_offset"],
                "effective_offset_seconds": item["effective_offset"],
                "confidence": item["sync_confidence"],
                "history": database.adjustment_history(str(item["evidence_id"])),
            }
            for item in database.list_evidence(investigation_id)
        ]

    return app


app = create_app()
