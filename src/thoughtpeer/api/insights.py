from __future__ import annotations

from fastapi import APIRouter

from ..core.deps import DbDep, UserDep
from ..repositories import insight_repo
from ..schemas.insight import InsightCreate, InsightResponse

router = APIRouter(prefix="/insights", tags=["insights"])


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


@router.get("/patterns/summary")
async def get_patterns(db: DbDep, user: UserDep):
    return await insight_repo.get_aggregated_patterns(db, user_id=user["id"])


@router.get("/timeline/mood")
async def mood_timeline(db: DbDep, user: UserDep):
    patterns = await insight_repo.get_aggregated_patterns(db, user_id=user["id"])
    return patterns["mood_trend"]
