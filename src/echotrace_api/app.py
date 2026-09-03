"""FastAPI application for a complete local Phase 1 investigation workflow."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Callable, Dict, List, Optional
from uuid import uuid4

import httpx
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing_extensions import Annotated

from echotrace_ai.context import build_evidence_context, filter_context_to_events
from echotrace_ai.graph import build_evidence_graph
from echotrace_ai.reasoning import EvidenceReasoner, create_reasoner
from echotrace_ai.search import EvidenceSearch, create_search
from echotrace_ai.video_intelligence import (
    VideoIntelligence,
    VideoIntelligenceError,
    create_video_intelligence,
)
from echotrace_evidence import process_evidence
from echotrace_sync.fusion import synchronize_pair
from echotrace_timeline import build_unified_timeline
from echotrace_video.detection import Detector, NullDetector
from echotrace_video.matching import match_tracks

from .auth import TokenError, TokenService, hash_password, verify_password
from .database import Database, utc_now
from .schemas import (
    EventCorrectionRequest,
    InvestigationCreate,
    LoginRequest,
    MatchReviewRequest,
    ObjectCorrectionRequest,
    QuestionRequest,
    RegisterRequest,
    SyncAdjustment,
    SynchronizationRequest,
)

SUPPORTED_EXTENSIONS = {".mp4", ".mov", ".jpg", ".jpeg", ".png", ".txt", ".pdf"}
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
    reasoner_factory: Optional[Callable[[], EvidenceReasoner]] = None,
    search_factory: Optional[Callable[[], EvidenceSearch]] = None,
    video_intelligence_factory: Optional[Callable[[], VideoIntelligence]] = None,
    require_auth: bool = True,
) -> FastAPI:
    root = Path(data_dir or os.environ.get("ECHOTRACE_DATA_DIR", "data")).resolve()
    uploads = root / "evidence"
    analysis_root = root / "analysis"
    uploads.mkdir(parents=True, exist_ok=True)
    analysis_root.mkdir(parents=True, exist_ok=True)
    database = Database(root / "echotrace.db")
    detector_factory = detector_factory or NullDetector
    reasoner_factory = reasoner_factory or create_reasoner
    search_factory = search_factory or create_search
    video_intelligence_factory = video_intelligence_factory or create_video_intelligence
    token_service = TokenService.from_data_dir(root)
    bearer = HTTPBearer(auto_error=False)

    app = FastAPI(
        title="EchoTrace Reconstruction API",
        version="0.6.0",
        description=(
            "Incident reconstruction and evidence-processing API. EchoTrace reconstructs evidence; "
            "it does not determine fault or liability."
        ),
    )
    origins = [
        value.strip()
        for value in os.environ.get(
            "ECHOTRACE_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
        ).split(",")
        if value.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.database = database
    app.state.data_dir = root

    def current_user(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer),  # noqa: B008
    ) -> Dict[str, object]:
        if not require_auth:
            return {"user_id": None, "name": "Local test user"}
        if credentials is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        try:
            claims = token_service.verify(credentials.credentials)
        except TokenError as error:
            raise HTTPException(status_code=401, detail=str(error)) from error
        user = database.get_user(str(claims["sub"]))
        if user is None:
            raise HTTPException(status_code=401, detail="User no longer exists")
        return user

    authenticated = Depends(current_user)

    def require_investigation(
        identifier: str, user: Dict[str, object]
    ) -> Dict[str, object]:
        investigation = database.get_investigation(identifier)
        if investigation is None or (
            require_auth and investigation.get("user_id") != user["user_id"]
        ):
            raise HTTPException(status_code=404, detail="Investigation not found")
        return investigation

    def investigation_context(
        identifier: str, user: Dict[str, object]
    ) -> Dict[str, object]:
        investigation = require_investigation(identifier, user)
        evidence_items = database.list_evidence(identifier)
        unified_timeline = public_timeline(
            identifier, corrected_timeline(identifier, evidence_items)
        )
        context = build_evidence_context(investigation, evidence_items, unified_timeline)
        context["objects"] = objects(identifier, user)
        context["object_matches"] = object_matches(identifier, user)
        return context

    def corrected_timeline(
        identifier: str, evidence_items: Optional[List[Dict[str, object]]] = None
    ) -> Dict[str, object]:
        result = build_unified_timeline(evidence_items or database.list_evidence(identifier))
        corrections = database.event_corrections(identifier)
        for event in result["events"]:
            saved = corrections.get(str(event["event_id"]))
            if saved:
                event.update(saved["correction"])
                event["review_status"] = "corrected"
                event["correction"] = {
                    "correction_id": saved["correction_id"],
                    "note": saved["note"],
                    "created_at": saved["created_at"],
                }
        result["events"].sort(key=lambda item: item["global_timestamp_seconds"])
        return result

    def public_evidence(item: Dict[str, object]) -> Dict[str, object]:
        return {
            key: value
            for key, value in item.items()
            if key not in {"storage_path", "analysis_path"}
        }

    def public_timeline(identifier: str, result: Dict[str, object]) -> Dict[str, object]:
        for event in result["events"]:
            for citation in event["evidence"]:
                frame_path = citation.pop("frame_path", None)
                if frame_path:
                    base = f"/investigations/{identifier}/evidence/{citation['evidence_id']}"
                    citation["frame_url"] = (
                        f"{base}/frames/{Path(str(frame_path)).name}"
                        if Path(str(frame_path)).parent.name == "frames"
                        else f"{base}/content"
                    )
        return result

    @app.get("/health")
    def health() -> Dict[str, str]:
        return {"status": "ok", "backend_phase": "4", "implementation_phase": "6"}

    @app.post("/auth/register", status_code=status.HTTP_201_CREATED)
    def register(payload: RegisterRequest) -> Dict[str, object]:
        try:
            user = database.create_user(
                payload.name, payload.email, hash_password(payload.password)
            )
        except sqlite3.IntegrityError as error:
            raise HTTPException(status_code=409, detail="Email already registered") from error
        return {
            "user": user,
            "access_token": token_service.issue(str(user["user_id"])),
            "token_type": "bearer",
        }

    @app.post("/auth/login")
    def login(payload: LoginRequest) -> Dict[str, object]:
        user = database.get_user_by_email(payload.email)
        if user is None or not verify_password(payload.password, str(user["password_hash"])):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        public = {key: value for key, value in user.items() if key != "password_hash"}
        return {
            "user": public,
            "access_token": token_service.issue(str(user["user_id"])),
            "token_type": "bearer",
        }

    @app.get("/auth/me")
    def authenticated_user(
        user: Dict[str, object] = authenticated,
    ) -> Dict[str, object]:
        return user

    @app.post("/investigations", status_code=status.HTTP_201_CREATED)
    def create_investigation(
        payload: InvestigationCreate, user: Dict[str, object] = authenticated
    ) -> Dict[str, object]:
        values = _serialize_request(payload)
        values["user_id"] = user["user_id"]
        return database.create_investigation(values)

    @app.get("/investigations")
    def list_investigations(
        user: Dict[str, object] = authenticated,
    ) -> List[Dict[str, object]]:
        return database.list_investigations(user["user_id"])

    @app.get("/investigations/{investigation_id}")
    def get_investigation(
        investigation_id: str, user: Dict[str, object] = authenticated
    ) -> Dict[str, object]:
        investigation = require_investigation(investigation_id, user)
        investigation["evidence"] = [
            public_evidence(item) for item in database.list_evidence(investigation_id)
        ]
        return investigation

    @app.delete("/investigations/{investigation_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_investigation(
        investigation_id: str, user: Dict[str, object] = authenticated
    ) -> Response:
        require_investigation(investigation_id, user)
        database.delete_investigation(investigation_id)
        return Response(status_code=204)

    @app.post(
        "/investigations/{investigation_id}/evidence", status_code=status.HTTP_201_CREATED
    )
    async def upload_evidence(
        investigation_id: str,
        file: Annotated[UploadFile, File()],
        user: Dict[str, object] = authenticated,
    ) -> Dict[str, object]:
        require_investigation(investigation_id, user)
        filename = Path(file.filename or "").name
        extension = Path(filename).suffix.lower()
        if extension not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=415,
                detail="Supported evidence: MP4, MOV, JPG, JPEG, PNG, TXT, or PDF",
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
        return public_evidence(database.add_evidence(values))

    @app.get("/investigations/{investigation_id}/evidence")
    def list_evidence(
        investigation_id: str, user: Dict[str, object] = authenticated
    ) -> List[Dict[str, object]]:
        require_investigation(investigation_id, user)
        return [public_evidence(item) for item in database.list_evidence(investigation_id)]

    @app.get("/investigations/{investigation_id}/evidence/{evidence_id}/content")
    def evidence_content(
        investigation_id: str,
        evidence_id: str,
        user: Dict[str, object] = authenticated,
    ) -> FileResponse:
        require_investigation(investigation_id, user)
        evidence = database.get_evidence(evidence_id)
        if evidence is None or evidence["investigation_id"] != investigation_id:
            raise HTTPException(status_code=404, detail="Evidence not found")
        return FileResponse(
            str(evidence["storage_path"]),
            media_type=str(evidence["media_type"]),
            filename=str(evidence["original_filename"]),
        )

    @app.get(
        "/investigations/{investigation_id}/evidence/{evidence_id}/frames/{frame_name}"
    )
    def evidence_frame(
        investigation_id: str,
        evidence_id: str,
        frame_name: str,
        user: Dict[str, object] = authenticated,
    ) -> FileResponse:
        require_investigation(investigation_id, user)
        evidence = database.get_evidence(evidence_id)
        if evidence is None or evidence["investigation_id"] != investigation_id:
            raise HTTPException(status_code=404, detail="Evidence not found")
        analysis_path = evidence.get("analysis_path")
        if not analysis_path:
            raise HTTPException(status_code=404, detail="Analysis not found")
        frames_dir = Path(str(analysis_path)).parent / "frames"
        target = (frames_dir / Path(frame_name).name).resolve()
        if target.parent != frames_dir.resolve() or not target.is_file():
            raise HTTPException(status_code=404, detail="Evidence frame not found")
        return FileResponse(str(target), media_type="image/jpeg")

    @app.post("/investigations/{investigation_id}/process")
    def process_investigation(
        investigation_id: str, user: Dict[str, object] = authenticated
    ) -> Dict[str, object]:
        require_investigation(investigation_id, user)
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
                manifest = process_evidence(
                    Path(str(evidence["storage_path"])),
                    output_dir,
                    detector_factory(),
                )
                if Path(str(evidence["storage_path"])).suffix.lower() in {".mp4", ".mov"}:
                    try:
                        enrichment = video_intelligence_factory().enrich(
                            Path(str(evidence["storage_path"]))
                        )
                        if enrichment:
                            manifest["video_intelligence"] = enrichment
                            extracted = [
                                str(item.get("text", ""))
                                for kind in ("transcript", "ocr")
                                for item in enrichment.get(kind, [])
                            ]
                            manifest["extracted_text"] = "\n".join(
                                text for text in extracted if text
                            )
                            (output_dir / "analysis.json").write_text(
                                json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
                            )
                    except (VideoIntelligenceError, httpx.HTTPError) as error:
                        manifest["video_intelligence_warning"] = str(error)
                        (output_dir / "analysis.json").write_text(
                            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
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
    def investigation_status(
        investigation_id: str, user: Dict[str, object] = authenticated
    ) -> Dict[str, object]:
        investigation = require_investigation(investigation_id, user)
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
    def timeline(
        investigation_id: str, user: Dict[str, object] = authenticated
    ) -> Dict[str, object]:
        require_investigation(investigation_id, user)
        return public_timeline(investigation_id, corrected_timeline(investigation_id))

    @app.patch("/investigations/{investigation_id}/timeline/{event_id}")
    def correct_timeline_event(
        investigation_id: str,
        event_id: str,
        payload: EventCorrectionRequest,
        user: Dict[str, object] = authenticated,
    ) -> Dict[str, object]:
        require_investigation(investigation_id, user)
        timeline_result = corrected_timeline(investigation_id)
        event = next(
            (item for item in timeline_result["events"] if item["event_id"] == event_id), None
        )
        if event is None:
            raise HTTPException(status_code=404, detail="Timeline event not found")
        correction = {}
        if payload.description is not None:
            correction["description"] = payload.description
        if payload.timestamp_seconds is not None:
            correction["global_timestamp_seconds"] = payload.timestamp_seconds
        if payload.confidence is not None:
            correction["confidence"] = payload.confidence
        return database.correct_event(
            investigation_id, event_id, event, correction, payload.note
        )

    @app.get("/investigations/{investigation_id}/objects")
    def objects(
        investigation_id: str, user: Dict[str, object] = authenticated
    ) -> List[Dict[str, object]]:
        require_investigation(investigation_id, user)
        observations = []
        for evidence in database.list_evidence(investigation_id):
            path = evidence.get("analysis_path")
            if path and Path(str(path)).is_file():
                analysis = json.loads(Path(str(path)).read_text(encoding="utf-8"))
                observations.extend(
                    {**item, "evidence_id": evidence["evidence_id"]}
                    for item in analysis.get("observations", [])
                )
        corrections = database.object_corrections(investigation_id)
        for observation in observations:
            saved = corrections.get(
                (str(observation["evidence_id"]), int(observation["track_id"]))
            )
            if saved:
                observation["canonical_identity"] = saved["canonical_identity"]
                observation["review_status"] = "corrected"
            frame_path = observation.pop("frame_path", None)
            if frame_path:
                base = (
                    f"/investigations/{investigation_id}/evidence/{observation['evidence_id']}"
                )
                observation["frame_url"] = (
                    f"{base}/frames/{Path(str(frame_path)).name}"
                    if Path(str(frame_path)).parent.name == "frames"
                    else f"{base}/content"
                )
        return observations

    @app.patch(
        "/investigations/{investigation_id}/objects/tracks/{evidence_id}/{track_id}"
    )
    def correct_object_identity(
        investigation_id: str,
        evidence_id: str,
        track_id: int,
        payload: ObjectCorrectionRequest,
        user: Dict[str, object] = authenticated,
    ) -> Dict[str, object]:
        require_investigation(investigation_id, user)
        available = {
            (str(item["evidence_id"]), int(item["track_id"]))
            for item in objects(investigation_id, user)
        }
        if (evidence_id, track_id) not in available:
            raise HTTPException(status_code=404, detail="Tracked object not found")
        return database.correct_object(
            investigation_id,
            evidence_id,
            track_id,
            payload.canonical_identity,
            payload.note,
        )

    @app.get("/investigations/{investigation_id}/objects/matches")
    def object_matches(
        investigation_id: str, user: Dict[str, object] = authenticated
    ) -> List[Dict[str, object]]:
        require_investigation(investigation_id, user)
        matches = match_tracks(database.list_evidence(investigation_id))
        reviews = database.match_reviews(investigation_id)
        for match in matches:
            review = reviews.get(str(match["match_id"]))
            if review:
                match["review_status"] = review["decision"]
                match["review"] = review
        return matches

    @app.patch("/investigations/{investigation_id}/objects/matches/{match_id}")
    def review_object_match(
        investigation_id: str,
        match_id: str,
        payload: MatchReviewRequest,
        user: Dict[str, object] = authenticated,
    ) -> Dict[str, object]:
        require_investigation(investigation_id, user)
        available = {
            str(item["match_id"])
            for item in match_tracks(database.list_evidence(investigation_id))
        }
        if match_id not in available:
            raise HTTPException(status_code=404, detail="Object match candidate not found")
        return database.review_match(
            investigation_id, match_id, payload.decision, payload.note
        )

    @app.patch(
        "/investigations/{investigation_id}/evidence/{evidence_id}/synchronization"
    )
    def adjust_synchronization(
        investigation_id: str,
        evidence_id: str,
        payload: SyncAdjustment,
        user: Dict[str, object] = authenticated,
    ) -> Dict[str, object]:
        require_investigation(investigation_id, user)
        evidence = database.get_evidence(evidence_id)
        if evidence is None or evidence["investigation_id"] != investigation_id:
            raise HTTPException(status_code=404, detail="Evidence not found")
        adjustment = database.adjust_offset(evidence_id, payload.offset_seconds, payload.note)
        return {
            "evidence_id": evidence_id,
            "effective_offset_seconds": payload.offset_seconds,
            "adjustment": adjustment,
        }

    @app.post("/investigations/{investigation_id}/synchronize")
    def automatically_synchronize(
        investigation_id: str,
        payload: SynchronizationRequest,
        user: Dict[str, object] = authenticated,
    ) -> Dict[str, object]:
        require_investigation(investigation_id, user)
        evidence_items = database.list_evidence(investigation_id)
        analyzed = [
            item
            for item in evidence_items
            if item["processing_status"] == "analyzed"
            and Path(str(item["storage_path"])).suffix.lower() in {".mp4", ".mov"}
        ]
        if len(analyzed) < 2:
            raise HTTPException(status_code=409, detail="Process at least two videos first")
        reference_id = payload.reference_evidence_id or str(analyzed[0]["evidence_id"])
        reference = next(
            (item for item in analyzed if item["evidence_id"] == reference_id), None
        )
        if reference is None:
            raise HTTPException(status_code=404, detail="Analyzed reference evidence not found")
        reference_details = {
            "offset_seconds": 0.0,
            "confidence": 1.0,
            "signals": [{"method": "reference", "offset_seconds": 0.0, "confidence": 1.0}],
            "warning": None,
        }
        database.update_sync_estimate(reference_id, 0.0, 1.0, reference_details)
        results = [{"evidence_id": reference_id, **reference_details}]
        for evidence in analyzed:
            if evidence["evidence_id"] == reference_id:
                continue
            result = synchronize_pair(reference, evidence, payload.max_offset_seconds).to_dict()
            database.update_sync_estimate(
                str(evidence["evidence_id"]),
                float(result["offset_seconds"]),
                float(result["confidence"]),
                result,
            )
            results.append({"evidence_id": evidence["evidence_id"], **result})
        database.set_investigation_status(
            investigation_id,
            "needs_review" if any(item.get("warning") for item in results) else "synchronized",
        )
        return {"reference_evidence_id": reference_id, "results": results}

    @app.get("/investigations/{investigation_id}/synchronization")
    def synchronization(
        investigation_id: str, user: Dict[str, object] = authenticated
    ) -> List[Dict[str, object]]:
        require_investigation(investigation_id, user)
        return [
            {
                "evidence_id": item["evidence_id"],
                "filename": item["original_filename"],
                "estimated_offset_seconds": item["estimated_offset"],
                "manual_offset_seconds": item["manual_offset"],
                "effective_offset_seconds": item["effective_offset"],
                "confidence": item["sync_confidence"],
                "details": item["sync_details"],
                "history": database.adjustment_history(str(item["evidence_id"])),
            }
            for item in database.list_evidence(investigation_id)
        ]

    @app.get("/investigations/{investigation_id}/summary")
    def incident_summary(
        investigation_id: str, user: Dict[str, object] = authenticated
    ) -> Dict[str, object]:
        context = investigation_context(investigation_id, user)
        search = search_factory()
        search.index_context(context)
        reasoner = reasoner_factory()
        response = reasoner.summarize(context)
        response["provider"] = reasoner.provider
        database.save_ai_response(investigation_id, None, response, reasoner.provider)
        return response

    @app.post("/investigations/{investigation_id}/ask")
    def ask_echotrace(
        investigation_id: str,
        payload: QuestionRequest,
        user: Dict[str, object] = authenticated,
    ) -> Dict[str, object]:
        context = investigation_context(investigation_id, user)
        search = search_factory()
        search.index_context(context)
        event_ids = search.search(payload.question, context)
        context = filter_context_to_events(context, event_ids)
        reasoner = reasoner_factory()
        response = reasoner.answer(payload.question, context)
        response["provider"] = reasoner.provider
        database.save_ai_response(
            investigation_id, payload.question, response, reasoner.provider
        )
        return response

    @app.get("/investigations/{investigation_id}/graph")
    def evidence_graph(
        investigation_id: str, user: Dict[str, object] = authenticated
    ) -> Dict[str, object]:
        investigation = require_investigation(investigation_id, user)
        evidence_items = database.list_evidence(investigation_id)
        unified_timeline = corrected_timeline(investigation_id, evidence_items)
        return build_evidence_graph(
            investigation,
            evidence_items,
            unified_timeline,
            objects(investigation_id, user),
            object_matches(investigation_id, user),
        )

    return app


app = create_app()
