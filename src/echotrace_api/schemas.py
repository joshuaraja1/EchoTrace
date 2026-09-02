"""Validated request models for the Phase 1 API."""

from __future__ import annotations

from datetime import date, time
from typing import Optional

from pydantic import BaseModel, Field


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

