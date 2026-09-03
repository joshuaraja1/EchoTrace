"""SQLite persistence for Phase 1 investigations and immutable evidence."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterator, List, Optional
from uuid import uuid4

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
  user_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS investigations (
  investigation_id TEXT PRIMARY KEY,
  user_id TEXT REFERENCES users(user_id),
  title TEXT NOT NULL,
  incident_type TEXT NOT NULL,
  incident_date TEXT NOT NULL,
  approximate_time TEXT,
  location TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS evidence (
  evidence_id TEXT PRIMARY KEY,
  investigation_id TEXT NOT NULL REFERENCES investigations(investigation_id) ON DELETE CASCADE,
  original_filename TEXT NOT NULL,
  media_type TEXT NOT NULL,
  storage_path TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  processing_status TEXT NOT NULL,
  metadata_json TEXT,
  analysis_path TEXT,
  estimated_offset REAL NOT NULL DEFAULT 0,
  manual_offset REAL,
  sync_confidence REAL,
  sync_details_json TEXT,
  uploaded_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sync_adjustments (
  adjustment_id TEXT PRIMARY KEY,
  evidence_id TEXT NOT NULL REFERENCES evidence(evidence_id) ON DELETE CASCADE,
  previous_offset REAL NOT NULL,
  new_offset REAL NOT NULL,
  note TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ai_responses (
  response_id TEXT PRIMARY KEY,
  investigation_id TEXT NOT NULL REFERENCES investigations(investigation_id) ON DELETE CASCADE,
  question TEXT,
  response_json TEXT NOT NULL,
  provider TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS match_reviews (
  review_id TEXT PRIMARY KEY,
  investigation_id TEXT NOT NULL REFERENCES investigations(investigation_id) ON DELETE CASCADE,
  match_id TEXT NOT NULL,
  decision TEXT NOT NULL,
  note TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS event_corrections (
  correction_id TEXT PRIMARY KEY,
  investigation_id TEXT NOT NULL REFERENCES investigations(investigation_id) ON DELETE CASCADE,
  event_id TEXT NOT NULL,
  original_json TEXT NOT NULL,
  correction_json TEXT NOT NULL,
  note TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS object_corrections (
  correction_id TEXT PRIMARY KEY,
  investigation_id TEXT NOT NULL REFERENCES investigations(investigation_id) ON DELETE CASCADE,
  evidence_id TEXT NOT NULL REFERENCES evidence(evidence_id) ON DELETE CASCADE,
  track_id INTEGER NOT NULL,
  canonical_identity TEXT NOT NULL,
  note TEXT,
  created_at TEXT NOT NULL
);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA)
            columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(evidence)").fetchall()
            }
            if "sync_details_json" not in columns:
                connection.execute("ALTER TABLE evidence ADD COLUMN sync_details_json TEXT")
            investigation_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(investigations)").fetchall()
            }
            if "user_id" not in investigation_columns:
                connection.execute("ALTER TABLE investigations ADD COLUMN user_id TEXT")

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def create_investigation(self, payload: Dict[str, object]) -> Dict[str, object]:
        identifier = str(uuid4())
        values = {
            "investigation_id": identifier,
            "user_id": payload["user_id"],
            "title": payload["title"],
            "incident_type": payload["incident_type"],
            "incident_date": payload["incident_date"],
            "approximate_time": payload.get("approximate_time"),
            "location": payload["location"],
            "description": payload.get("description"),
            "status": "created",
            "created_at": utc_now(),
        }
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO investigations
                (investigation_id, user_id, title, incident_type, incident_date, approximate_time,
                 location, description, status, created_at) VALUES
                (:investigation_id, :user_id, :title, :incident_type, :incident_date,
                 :approximate_time, :location, :description, :status, :created_at)""",
                values,
            )
        return values

    def list_investigations(self, user_id: str) -> List[Dict[str, object]]:
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT * FROM investigations WHERE user_id = ?
                ORDER BY created_at DESC""",
                (user_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_investigation(self, identifier: str) -> Optional[Dict[str, object]]:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM investigations WHERE investigation_id = ?", (identifier,)
            ).fetchone()
        return dict(row) if row else None

    def create_user(self, name: str, email: str, password_hash: str) -> Dict[str, object]:
        value = {
            "user_id": str(uuid4()),
            "name": name,
            "email": email.lower(),
            "password_hash": password_hash,
            "created_at": utc_now(),
        }
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO users (user_id, name, email, password_hash, created_at)
                VALUES (:user_id, :name, :email, :password_hash, :created_at)""",
                value,
            )
        return {key: item for key, item in value.items() if key != "password_hash"}

    def get_user_by_email(self, email: str) -> Optional[Dict[str, object]]:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM users WHERE email = ?", (email.lower(),)
            ).fetchone()
        return dict(row) if row else None

    def get_user(self, user_id: str) -> Optional[Dict[str, object]]:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT user_id, name, email, created_at FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        return dict(row) if row else None

    def delete_investigation(self, identifier: str) -> bool:
        with self.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM investigations WHERE investigation_id = ?", (identifier,)
            )
        return cursor.rowcount > 0

    def add_evidence(self, values: Dict[str, object]) -> Dict[str, object]:
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO evidence
                (evidence_id, investigation_id, original_filename, media_type, storage_path,
                 sha256, processing_status, uploaded_at)
                VALUES (:evidence_id, :investigation_id, :original_filename, :media_type,
                        :storage_path, :sha256, :processing_status, :uploaded_at)""",
                values,
            )
        return values

    def list_evidence(self, investigation_id: str) -> List[Dict[str, object]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM evidence WHERE investigation_id = ? ORDER BY uploaded_at",
                (investigation_id,),
            ).fetchall()
        return [self._decode_evidence(row) for row in rows]

    def get_evidence(self, evidence_id: str) -> Optional[Dict[str, object]]:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM evidence WHERE evidence_id = ?", (evidence_id,)
            ).fetchone()
        return self._decode_evidence(row) if row else None

    @staticmethod
    def _decode_evidence(row: sqlite3.Row) -> Dict[str, object]:
        value = dict(row)
        value["metadata"] = json.loads(value.pop("metadata_json")) if value["metadata_json"] else None
        details = value.pop("sync_details_json", None)
        value["sync_details"] = json.loads(details) if details else None
        value["effective_offset"] = (
            value["manual_offset"] if value["manual_offset"] is not None else value["estimated_offset"]
        )
        return value

    def mark_processing(self, evidence_id: str) -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE evidence SET processing_status = 'processing' WHERE evidence_id = ?",
                (evidence_id,),
            )

    def mark_analyzed(
        self, evidence_id: str, metadata: Dict[str, object], analysis_path: Path
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """UPDATE evidence SET processing_status = 'analyzed', metadata_json = ?,
                analysis_path = ? WHERE evidence_id = ?""",
                (json.dumps(metadata), str(analysis_path), evidence_id),
            )

    def mark_failed(self, evidence_id: str, message: str) -> None:
        with self.connect() as connection:
            connection.execute(
                """UPDATE evidence SET processing_status = 'failed',
                metadata_json = ? WHERE evidence_id = ?""",
                (json.dumps({"error": message}), evidence_id),
            )

    def update_sync_estimate(
        self,
        evidence_id: str,
        offset: float,
        confidence: float,
        details: Dict[str, object],
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """UPDATE evidence SET estimated_offset = ?, sync_confidence = ?,
                sync_details_json = ? WHERE evidence_id = ?""",
                (offset, confidence, json.dumps(details), evidence_id),
            )

    def set_investigation_status(self, identifier: str, status: str) -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE investigations SET status = ? WHERE investigation_id = ?",
                (status, identifier),
            )

    def adjust_offset(
        self, evidence_id: str, new_offset: float, note: Optional[str]
    ) -> Dict[str, object]:
        evidence = self.get_evidence(evidence_id)
        if evidence is None:
            raise KeyError(evidence_id)
        previous = float(evidence["effective_offset"])
        adjustment = {
            "adjustment_id": str(uuid4()),
            "evidence_id": evidence_id,
            "previous_offset": previous,
            "new_offset": new_offset,
            "note": note,
            "created_at": utc_now(),
        }
        with self.connect() as connection:
            connection.execute(
                "UPDATE evidence SET manual_offset = ? WHERE evidence_id = ?",
                (new_offset, evidence_id),
            )
            connection.execute(
                """INSERT INTO sync_adjustments VALUES
                (:adjustment_id, :evidence_id, :previous_offset, :new_offset, :note, :created_at)""",
                adjustment,
            )
        return adjustment

    def adjustment_history(self, evidence_id: str) -> List[Dict[str, object]]:
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT * FROM sync_adjustments WHERE evidence_id = ?
                ORDER BY created_at""",
                (evidence_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def save_ai_response(
        self,
        investigation_id: str,
        question: Optional[str],
        response: Dict[str, object],
        provider: str,
    ) -> Dict[str, object]:
        value = {
            "response_id": str(uuid4()),
            "investigation_id": investigation_id,
            "question": question,
            "response_json": json.dumps(response),
            "provider": provider,
            "created_at": utc_now(),
        }
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO ai_responses VALUES
                (:response_id, :investigation_id, :question, :response_json, :provider, :created_at)""",
                value,
            )
        return {**value, "response": response}

    def review_match(
        self, investigation_id: str, match_id: str, decision: str, note: Optional[str]
    ) -> Dict[str, object]:
        value = {
            "review_id": str(uuid4()),
            "investigation_id": investigation_id,
            "match_id": match_id,
            "decision": decision,
            "note": note,
            "created_at": utc_now(),
        }
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO match_reviews VALUES
                (:review_id, :investigation_id, :match_id, :decision, :note, :created_at)""",
                value,
            )
        return value

    def match_reviews(self, investigation_id: str) -> Dict[str, Dict[str, object]]:
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT * FROM match_reviews WHERE investigation_id = ?
                ORDER BY created_at""",
                (investigation_id,),
            ).fetchall()
        return {str(row["match_id"]): dict(row) for row in rows}

    def correct_event(
        self,
        investigation_id: str,
        event_id: str,
        original: Dict[str, object],
        correction: Dict[str, object],
        note: Optional[str],
    ) -> Dict[str, object]:
        value = {
            "correction_id": str(uuid4()),
            "investigation_id": investigation_id,
            "event_id": event_id,
            "original_json": json.dumps(original),
            "correction_json": json.dumps(correction),
            "note": note,
            "created_at": utc_now(),
        }
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO event_corrections VALUES
                (:correction_id, :investigation_id, :event_id, :original_json,
                 :correction_json, :note, :created_at)""",
                value,
            )
        return {**value, "original": original, "correction": correction}

    def event_corrections(self, investigation_id: str) -> Dict[str, Dict[str, object]]:
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT * FROM event_corrections WHERE investigation_id = ?
                ORDER BY created_at""",
                (investigation_id,),
            ).fetchall()
        return {
            str(row["event_id"]): {
                **dict(row),
                "original": json.loads(row["original_json"]),
                "correction": json.loads(row["correction_json"]),
            }
            for row in rows
        }

    def correct_object(
        self,
        investigation_id: str,
        evidence_id: str,
        track_id: int,
        canonical_identity: str,
        note: Optional[str],
    ) -> Dict[str, object]:
        value = {
            "correction_id": str(uuid4()),
            "investigation_id": investigation_id,
            "evidence_id": evidence_id,
            "track_id": track_id,
            "canonical_identity": canonical_identity,
            "note": note,
            "created_at": utc_now(),
        }
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO object_corrections VALUES
                (:correction_id, :investigation_id, :evidence_id, :track_id,
                 :canonical_identity, :note, :created_at)""",
                value,
            )
        return value

    def object_corrections(self, investigation_id: str) -> Dict[tuple, Dict[str, object]]:
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT * FROM object_corrections WHERE investigation_id = ?
                ORDER BY created_at""",
                (investigation_id,),
            ).fetchall()
        return {(str(row["evidence_id"]), int(row["track_id"])): dict(row) for row in rows}
