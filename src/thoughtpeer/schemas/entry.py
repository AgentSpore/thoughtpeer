from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Mood(str, Enum):
    great = "great"
    good = "good"
    neutral = "neutral"
    bad = "bad"
    terrible = "terrible"


class EntryCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000)
    mood: Mood = Mood.neutral
    tags: list[str] = Field(default_factory=list)


class EntryUpdate(BaseModel):
    text: str | None = Field(None, min_length=1, max_length=10000)
    mood: Mood | None = None
    tags: list[str] | None = None


class EntryResolve(BaseModel):
    resolution_text: str = Field(..., min_length=1, max_length=5000)


class EntryResponse(BaseModel):
    id: int
    user_id: int
    text: str
    mood: str
    tags: list[str]
    is_resolved: bool
    resolution_text: str | None
    created_at: datetime
    updated_at: datetime


class EntryListParams(BaseModel):
    mood: Mood | None = None
    tag: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    resolved: bool | None = None
    limit: int = Field(50, ge=1, le=200)
    offset: int = Field(0, ge=0)
