from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class InsightResponse(BaseModel):
    id: int
    entry_id: int
    problems: list[str]
    emotions: list[str]
    category: str | None
    severity: int
    keywords: list[str]
    created_at: datetime


class InsightCreate(BaseModel):
    """Sent from client (local LLM analysis result)."""
    problems: list[str] = Field(default_factory=list)
    emotions: list[str] = Field(default_factory=list)
    category: str | None = None
    severity: int = Field(5, ge=1, le=10)
    keywords: list[str] = Field(default_factory=list)


class PatternResponse(BaseModel):
    top_problems: list[dict]
    top_emotions: list[dict]
    top_categories: list[dict]
    mood_trend: list[dict]
    total_entries: int
    resolved_count: int


class TimelinePoint(BaseModel):
    date: str
    mood: str
    entry_count: int
