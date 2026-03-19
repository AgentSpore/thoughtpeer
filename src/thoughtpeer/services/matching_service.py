"""Peer matching via Jaccard similarity on tags/keywords.

For MVP we use simple set-based matching. In production,
this would use vector embeddings from the local LLM.
"""

from __future__ import annotations

import aiosqlite

from ..repositories import peer_repo
from ..schemas.peer import PeerSearchQuery


async def find_similar(db: aiosqlite.Connection, query: PeerSearchQuery) -> list[dict]:
    keywords = query.keywords
    tags = query.tags

    # If text provided, extract keywords from it (simple split)
    if query.text and not keywords:
        words = set(query.text.lower().split())
        stopwords = {"the", "a", "an", "is", "are", "was", "were", "i", "my", "me",
                     "to", "and", "of", "in", "it", "for", "on", "at", "do", "so"}
        keywords = [w for w in words if len(w) >= 4 and w not in stopwords][:10]

    return await peer_repo.search_similar(
        db,
        category=query.category,
        keywords=keywords,
        tags=tags,
        limit=query.limit,
    )


async def find_solutions(db: aiosqlite.Connection, query: PeerSearchQuery) -> list[dict]:
    keywords = query.keywords
    tags = query.tags

    if query.text and not keywords:
        words = set(query.text.lower().split())
        stopwords = {"the", "a", "an", "is", "are", "was", "were", "i", "my", "me",
                     "to", "and", "of", "in", "it", "for", "on", "at", "do", "so"}
        keywords = [w for w in words if len(w) >= 4 and w not in stopwords][:10]

    return await peer_repo.search_solutions(
        db,
        category=query.category,
        keywords=keywords,
        tags=tags,
        limit=query.limit,
    )
