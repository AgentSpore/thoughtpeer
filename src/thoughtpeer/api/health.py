from __future__ import annotations

from fastapi import APIRouter

from ..core.deps import DbDep
from ..repositories import entry_repo, peer_repo

router = APIRouter(tags=["system"])


@router.get("/health")
async def health(db: DbDep):
    entry_count = await entry_repo.count_entries(db)
    pool = await peer_repo.pool_stats(db)
    return {
        "status": "healthy",
        "entries": entry_count,
        "peer_pool": pool,
    }


@router.get("/analytics/overview")
async def overview(db: DbDep):
    from ..repositories import insight_repo
    entry_count = await entry_repo.count_entries(db)
    pool = await peer_repo.pool_stats(db)
    patterns = await insight_repo.get_aggregated_patterns(db)
    return {
        "total_entries": entry_count,
        "resolved_entries": patterns["resolved_count"],
        "top_problems": patterns["top_problems"][:5],
        "top_emotions": patterns["top_emotions"][:5],
        "peer_pool_size": pool["total"],
        "peer_solutions": pool["resolved"],
    }
