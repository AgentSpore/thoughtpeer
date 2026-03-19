from __future__ import annotations

from fastapi import APIRouter

from ..core.deps import DbDep, UserDep
from ..schemas.peer import PeerMatch, PeerSearchQuery, PeerShareRequest, PeerSolution
from ..services import matching_service, peer_service

router = APIRouter(prefix="/peers", tags=["peers"])


@router.post("/similar", response_model=list[PeerMatch])
async def find_similar(query: PeerSearchQuery, db: DbDep, user: UserDep):
    return await matching_service.find_similar(db, query)


@router.post("/solutions", response_model=list[PeerSolution])
async def find_solutions(query: PeerSearchQuery, db: DbDep, user: UserDep):
    return await matching_service.find_solutions(db, query)


@router.post("/share", status_code=201)
async def share_to_pool(data: PeerShareRequest, db: DbDep, user: UserDep):
    return await peer_service.share_to_pool(db, user["id"], data)


@router.get("/stats")
async def pool_stats(db: DbDep, user: UserDep):
    return await peer_service.get_pool_stats(db)
