from __future__ import annotations

import aiosqlite

from ..repositories import peer_repo
from ..schemas.peer import PeerShareRequest


async def share_to_pool(db: aiosqlite.Connection, user_id: int, data: PeerShareRequest) -> dict:
    return await peer_repo.add_to_pool(
        db,
        user_id=user_id,
        category=data.category,
        tags=data.tags,
        keywords=data.keywords,
        severity=data.severity,
        mood=data.mood,
        is_resolved=data.is_resolved,
        resolution_text=data.resolution_text,
    )


async def get_pool_stats(db: aiosqlite.Connection) -> dict:
    return await peer_repo.pool_stats(db)


async def remove_from_pool(db: aiosqlite.Connection, peer_id: int, user_id: int) -> None:
    from fastapi import HTTPException
    entry = await peer_repo.get_peer_entry(db, peer_id)
    if not entry:
        raise HTTPException(404, "Peer entry not found")
    if int(entry["user_id"]) != user_id:
        raise HTTPException(403, "Not your peer entry")
    await peer_repo.delete_peer_entry(db, peer_id)
