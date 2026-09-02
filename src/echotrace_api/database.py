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
CREATE TABLE IF NOT EXISTS investigations (
  investigation_id TEXT PRIMARY KEY,
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
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA)

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
                """INSERT INTO investigations VALUES
                (:investigation_id, :title, :incident_type, :incident_date, :approximate_time,
                 :location, :description, :status, :created_at)""",
                values,
            )
        return values

    def list_investigations(self) -> List[Dict[str, object]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM investigations ORDER BY created_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def get_investigation(self, identifier: str) -> Optional[Dict[str, object]]:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM investigations WHERE investigation_id = ?", (identifier,)
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
