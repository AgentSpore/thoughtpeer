from __future__ import annotations

from fastapi import APIRouter

from ..core.deps import DbDep, UserDep
from ..repositories import insight_repo
from ..schemas.insight import InsightCreate, InsightResponse
from ..services import timeline_service

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/patterns/summary")
async def get_patterns(db: DbDep, user: UserDep):
    return await insight_repo.get_aggregated_patterns(db, user_id=user["id"])


@router.get("/timeline")
async def timeline(db: DbDep, user: UserDep):
    """Mood timeline with 7-day moving average and trend classification."""
    return await timeline_service.build_timeline(db, user_id=user["id"])


# Legacy compat — kept so old clients don't break.
@router.get("/timeline/mood")
async def mood_timeline(db: DbDep, user: UserDep):
    data = await timeline_service.build_timeline(db, user_id=user["id"])
    return data["points"]


@router.post("/{entry_id}", response_model=InsightResponse)
async def submit_insight(entry_id: int, data: InsightCreate, db: DbDep, user: UserDep):
    return await insight_repo.upsert_insight(
        db, entry_id=entry_id,
        problems=data.problems, emotions=data.emotions,
        category=data.category, severity=data.severity,
        keywords=data.keywords,
    )


@router.get("/{entry_id}")
async def get_insight(entry_id: int, db: DbDep, user: UserDep):
    return await insight_repo.get_insight_by_entry(db, entry_id)
