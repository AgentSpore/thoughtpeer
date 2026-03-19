from __future__ import annotations

import hashlib
import json
from datetime import datetime

import aiosqlite


async def add_to_pool(
    db: aiosqlite.Connection,
    *,
    user_id: int,
    category: str,
    tags: list[str],
    keywords: list[str],
    severity: int,
    mood: str | None,
    is_resolved: bool,
    resolution_text: str | None,
) -> dict:
    anon_hash = hashlib.sha256(
        f"{user_id}:{category}:{','.join(sorted(tags))}:{datetime.utcnow().isoformat()}".encode()
    ).hexdigest()[:16]

    now = datetime.utcnow().isoformat()
    cursor = await db.execute(
        """INSERT INTO peer_pool
           (user_id, anon_hash, category, tags, keywords, severity, mood, is_resolved, resolution_text, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, anon_hash, category, json.dumps(tags), json.dumps(keywords),
         severity, mood, int(is_resolved), resolution_text, now),
    )
    await db.commit()
    return await get_peer_entry(db, cursor.lastrowid)


async def get_peer_entry(db: aiosqlite.Connection, peer_id: int) -> dict | None:
    cursor = await db.execute("SELECT * FROM peer_pool WHERE id = ?", (peer_id,))
    row = await cursor.fetchone()
    if not row:
        return None
    return _row_to_dict(row)


async def search_similar(
    db: aiosqlite.Connection, *, category: str | None = None,
    keywords: list[str] | None = None, tags: list[str] | None = None, limit: int = 10,
) -> list[dict]:
    query = "SELECT * FROM peer_pool WHERE 1=1"
    params: list = []
    if category:
        query += " AND category = ?"
        params.append(category)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit * 3)

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    results = [_row_to_dict(r) for r in rows]

    search_terms = set(keywords or []) | set(tags or [])
    for r in results:
        peer_terms = set(r["keywords"]) | set(r["tags"])
        if search_terms and peer_terms:
            r["similarity"] = len(search_terms & peer_terms) / len(search_terms | peer_terms)
        else:
            r["similarity"] = 0.3 if r.get("category") == category else 0.1
    results.sort(key=lambda x: -x["similarity"])
    return results[:limit]


async def search_solutions(
    db: aiosqlite.Connection, *, category: str | None = None,
    keywords: list[str] | None = None, tags: list[str] | None = None, limit: int = 10,
) -> list[dict]:
    query = "SELECT * FROM peer_pool WHERE is_resolved = 1 AND resolution_text IS NOT NULL"
    params: list = []
    if category:
        query += " AND category = ?"
        params.append(category)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit * 3)

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    results = [_row_to_dict(r) for r in rows]

    search_terms = set(keywords or []) | set(tags or [])
    for r in results:
        peer_terms = set(r["keywords"]) | set(r["tags"])
        if search_terms and peer_terms:
            r["similarity"] = len(search_terms & peer_terms) / len(search_terms | peer_terms)
        else:
            r["similarity"] = 0.3
    results.sort(key=lambda x: -x["similarity"])
    return results[:limit]


async def pool_stats(db: aiosqlite.Connection) -> dict:
    total = await db.execute("SELECT COUNT(*) FROM peer_pool")
    resolved = await db.execute("SELECT COUNT(*) FROM peer_pool WHERE is_resolved = 1")
    return {"total": (await total.fetchone())[0], "resolved": (await resolved.fetchone())[0]}


def _row_to_dict(row: aiosqlite.Row) -> dict:
    d = dict(row)
    d["tags"] = json.loads(d.get("tags") or "[]")
    d["keywords"] = json.loads(d.get("keywords") or "[]")
    d["is_resolved"] = bool(d.get("is_resolved"))
    return d
