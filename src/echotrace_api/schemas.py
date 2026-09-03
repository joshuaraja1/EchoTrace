"""Validated request models for the Phase 1 API."""

from __future__ import annotations

from datetime import date, time
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=10, max_length=256)


class LoginRequest(BaseModel):
    email: str
    password: str


class InvestigationCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    incident_type: str = Field(min_length=1, max_length=80)
    incident_date: date
    approximate_time: Optional[time] = None
    location: str = Field(min_length=1, max_length=300)
    description: Optional[str] = Field(default=None, max_length=2000)


class SyncAdjustment(BaseModel):
    offset_seconds: float = Field(ge=-3600, le=3600)
    note: Optional[str] = Field(default=None, max_length=500)


class SynchronizationRequest(BaseModel):
    reference_evidence_id: Optional[str] = None
    max_offset_seconds: float = Field(default=60, gt=0, le=3600)


class QuestionRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


class MatchReviewRequest(BaseModel):
    decision: str = Field(pattern=r"^(confirmed|rejected)$")
    note: Optional[str] = Field(default=None, max_length=500)


class EventCorrectionRequest(BaseModel):
    description: Optional[str] = Field(default=None, min_length=1, max_length=1000)
    timestamp_seconds: Optional[float] = Field(default=None, ge=0, le=86_400)
    confidence: Optional[float] = Field(default=None, ge=0, le=1)
    note: Optional[str] = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def require_change(self) -> EventCorrectionRequest:
        if self.description is None and self.timestamp_seconds is None and self.confidence is None:
            raise ValueError("At least one event field must be corrected")
        return self


class ObjectCorrectionRequest(BaseModel):
    canonical_identity: str = Field(min_length=1, max_length=120)
    note: Optional[str] = Field(default=None, max_length=500)
