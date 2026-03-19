from __future__ import annotations

from fastapi import APIRouter

from ..core.deps import DbDep
from ..repositories import insight_repo
from ..schemas.insight import InsightCreate, InsightResponse

router = APIRouter(prefix="/insights", tags=["insights"])


@router.post("/{entry_id}", response_model=InsightResponse)
async def submit_insight(entry_id: int, data: InsightCreate, db: DbDep):
    """Submit insight from local LLM analysis."""
    return await insight_repo.upsert_insight(
        db,
        entry_id=entry_id,
        problems=data.problems,
        emotions=data.emotions,
        category=data.category,
        severity=data.severity,
        keywords=data.keywords,
    )


@router.get("/{entry_id}", response_model=InsightResponse | None)
async def get_insight(entry_id: int, db: DbDep):
    return await insight_repo.get_insight_by_entry(db, entry_id)


@router.get("/patterns/summary")
async def get_patterns(db: DbDep):
    return await insight_repo.get_aggregated_patterns(db)


@router.get("/timeline/mood")
async def mood_timeline(db: DbDep):
    patterns = await insight_repo.get_aggregated_patterns(db)
    return patterns["mood_trend"]
