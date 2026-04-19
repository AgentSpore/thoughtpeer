"""Peer matching via cosine similarity on token bags.

For v0.3 we upgrade from raw Jaccard (set intersection in peer_repo) to
cosine similarity on bag-of-tokens, sorted desc and capped at 5 peers
to avoid overwhelming the user. The cosine_similarity function is pure
(no DB deps) so we can unit-test it in tests/test_matching.py.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Iterable

import aiosqlite

from ..repositories import peer_repo
from ..schemas.peer import PeerSearchQuery

_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "i", "my", "me",
    "to", "and", "of", "in", "it", "for", "on", "at", "do", "so",
    "but", "or", "with", "as", "that", "this", "be", "been",
}

_MAX_PEERS = 5
_RESOLVED_THRESHOLD = 0.5


def tokenize(text: str) -> list[str]:
    """Extract meaningful tokens from free text."""
    if not text:
        return []
    words = text.lower().replace("\n", " ").split()
    return [w.strip(".,!?;:()[]\"'") for w in words
            if len(w) >= 4 and w.lower() not in _STOPWORDS][:50]


def cosine_similarity(a: Iterable[str], b: Iterable[str]) -> float:
    """Cosine similarity on token bags. Returns float in [0, 1].

    Pure function — no DB, no side effects. Unit tested.
    """
    ca, cb = Counter(a), Counter(b)
    if not ca or not cb:
        return 0.0
    shared = set(ca) & set(cb)
    dot = sum(ca[t] * cb[t] for t in shared)
    norm_a = math.sqrt(sum(v * v for v in ca.values()))
    norm_b = math.sqrt(sum(v * v for v in cb.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _query_terms(query: PeerSearchQuery) -> list[str]:
    terms: list[str] = list(query.keywords) + list(query.tags)
    if query.text:
        terms.extend(tokenize(query.text))
    return [t.lower() for t in terms if t]


def _peer_terms(peer: dict) -> list[str]:
    summary = peer.get("summary") or peer.get("resolution_text") or ""
    return [t.lower() for t in
            list(peer.get("keywords") or []) + list(peer.get("tags") or [])
            + tokenize(summary)]


async def find_similar(db: aiosqlite.Connection, query: PeerSearchQuery) -> list[dict]:
    # Pull a wider candidate pool via category filter, then rescore via cosine.
    candidates = await peer_repo.search_similar(
        db, category=query.category, keywords=query.keywords,
        tags=query.tags, limit=max(query.limit * 3, 30),
    )
    q_terms = _query_terms(query)
    for peer in candidates:
        score = cosine_similarity(q_terms, _peer_terms(peer))
        peer["similarity"] = round(score, 4)
        peer["similarity_score"] = round(score, 4)
    candidates.sort(key=lambda p: -p["similarity_score"])
    return candidates[:min(query.limit, _MAX_PEERS)]


async def find_solutions(db: aiosqlite.Connection, query: PeerSearchQuery) -> list[dict]:
    candidates = await peer_repo.search_solutions(
        db, category=query.category, keywords=query.keywords,
        tags=query.tags, limit=max(query.limit * 3, 30),
    )
    q_terms = _query_terms(query)
    for peer in candidates:
        score = cosine_similarity(q_terms, _peer_terms(peer))
        peer["similarity"] = round(score, 4)
        peer["similarity_score"] = round(score, 4)
    candidates.sort(key=lambda p: -p["similarity_score"])
    return candidates[:min(query.limit, _MAX_PEERS)]


async def find_resolved_for_entry(
    db: aiosqlite.Connection, *, entry_terms: list[str], category: str | None,
    threshold: float = _RESOLVED_THRESHOLD, limit: int = _MAX_PEERS,
) -> list[dict]:
    """Find resolved peers whose token bag cosine > threshold vs entry_terms."""
    candidates = await peer_repo.search_solutions(
        db, category=category, keywords=None, tags=None, limit=100,
    )
    q = [t.lower() for t in entry_terms if t]
    scored: list[dict] = []
    for peer in candidates:
        if not peer.get("resolution_text"):
            continue
        score = cosine_similarity(q, _peer_terms(peer))
        if score >= threshold:
            peer["similarity_score"] = round(score, 4)
            scored.append(peer)
    scored.sort(key=lambda p: -p["similarity_score"])
    return scored[:limit]
