from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PeerShareRequest(BaseModel):
    """Share anonymized insight to the peer pool."""
    category: str = Field(..., min_length=1, max_length=100)
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    severity: int = Field(5, ge=1, le=10)
    mood: str | None = None
    is_resolved: bool = False
    resolution_text: str | None = Field(None, max_length=5000)


class PeerMatch(BaseModel):
    id: int
    category: str
    tags: list[str]
    keywords: list[str]
    severity: int
    mood: str | None
    is_resolved: bool
    resolution_text: str | None
    similarity: float
    created_at: datetime


class PeerSolution(BaseModel):
    id: int
    category: str
    tags: list[str]
    resolution_text: str
    severity: int
    similarity: float
    created_at: datetime


class PeerSearchQuery(BaseModel):
    text: str | None = None
    category: str | None = None
    keywords: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    limit: int = Field(10, ge=1, le=50)
