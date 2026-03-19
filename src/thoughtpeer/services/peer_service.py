from __future__ import annotations

import aiosqlite

from ..repositories import peer_repo
from ..schemas.peer import PeerShareRequest


async def share_to_pool(db: aiosqlite.Connection, data: PeerShareRequest) -> dict:
    return await peer_repo.add_to_pool(
        db,
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
