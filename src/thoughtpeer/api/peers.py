from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..core.deps import DbDep, UserDep
from ..repositories import insight_repo
from ..schemas.peer import (
    PeerMatch,
    PeerResolvedSimilar,
    PeerSearchQuery,
    PeerShareRequest,
    PeerSolution,
)
from ..services import entry_service, matching_service, peer_service

router = APIRouter(prefix="/peers", tags=["peers"])


@router.post("/similar", response_model=list[PeerMatch])
async def find_similar(query: PeerSearchQuery, db: DbDep, user: UserDep):
    return await matching_service.find_similar(db, query)


@router.post("/solutions", response_model=list[PeerSolution])
async def find_solutions(query: PeerSearchQuery, db: DbDep, user: UserDep):
    return await matching_service.find_solutions(db, query)


@router.get("/resolved-similar/{entry_id}", response_model=list[PeerResolvedSimilar])
async def resolved_similar(entry_id: int, db: DbDep, user: UserDep):
    """Return resolved peers whose pattern matches this entry (cosine > 0.5).

    Drives the "how similar problems were resolved by others" panel
    on the entry detail page.
    """
    entry = await entry_service.get(db, entry_id, user["id"])
    insight = await insight_repo.get_insight_by_entry(db, entry_id)

    terms: list[str] = []
    category: str | None = None
    if insight:
        terms.extend(insight.get("keywords") or [])
        category = insight.get("category")
    terms.extend(entry.get("tags") or [])
    terms.extend(matching_service.tokenize(entry.get("text") or ""))

    peers = await matching_service.find_resolved_for_entry(
        db, entry_terms=terms, category=category,
    )
    return [
        {
            "anon_hash": p["anon_hash"],
            "category": p["category"],
            "tags": p["tags"],
            "similarity_score": p["similarity_score"],
            "resolution_text": p["resolution_text"],
            "severity": p["severity"],
            "created_at": p["created_at"],
        }
        for p in peers
    ]


@router.post("/share", status_code=201)
async def share_to_pool(data: PeerShareRequest, db: DbDep, user: UserDep):
    return await peer_service.share_to_pool(db, user["id"], data)


@router.delete("/share/{peer_id}", status_code=204)
async def unshare(peer_id: int, db: DbDep, user: UserDep):
    await peer_service.remove_from_pool(db, peer_id, user["id"])


@router.get("/stats")
async def pool_stats(db: DbDep, user: UserDep):
    return await peer_service.get_pool_stats(db)
