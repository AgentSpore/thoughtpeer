from __future__ import annotations

import json
from datetime import datetime

import aiosqlite


async def create_entry(
    db: aiosqlite.Connection,
    *,
    user_id: int,
    text: str,
    mood: str,
    tags: list[str],
) -> dict:
    now = datetime.utcnow().isoformat()
    cursor = await db.execute(
        """INSERT INTO entries (user_id, text, mood, tags, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, text, mood, json.dumps(tags), now, now),
    )
    await db.commit()
    return await get_entry(db, cursor.lastrowid)


async def get_entry(db: aiosqlite.Connection, entry_id: int) -> dict | None:
    cursor = await db.execute("SELECT * FROM entries WHERE id = ?", (entry_id,))
    row = await cursor.fetchone()
    if not row:
        return None
    return _row_to_dict(row)


async def list_entries(
    db: aiosqlite.Connection,
    *,
    user_id: int = 0,
    mood: str | None = None,
    tag: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    resolved: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    query = "SELECT * FROM entries WHERE user_id = ?"
    params: list = [user_id]

    if mood:
        query += " AND mood = ?"
        params.append(mood)
    if tag:
        query += " AND tags LIKE ?"
        params.append(f'%"{tag}"%')
    if date_from:
        query += " AND created_at >= ?"
        params.append(date_from)
    if date_to:
        query += " AND created_at <= ?"
        params.append(date_to)
    if resolved is not None:
        query += " AND is_resolved = ?"
        params.append(int(resolved))

    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    return [_row_to_dict(r) for r in rows]


async def update_entry(
    db: aiosqlite.Connection,
    entry_id: int,
    **fields,
) -> dict | None:
    sets = []
    params = []
    for key, val in fields.items():
        if val is not None:
            if key == "tags":
                val = json.dumps(val)
            sets.append(f"{key} = ?")
            params.append(val)

    if not sets:
        return await get_entry(db, entry_id)

    sets.append("updated_at = ?")
    params.append(datetime.utcnow().isoformat())
    params.append(entry_id)

    await db.execute(
        f"UPDATE entries SET {', '.join(sets)} WHERE id = ?", params
    )
    await db.commit()
    return await get_entry(db, entry_id)


async def resolve_entry(
    db: aiosqlite.Connection, entry_id: int, resolution_text: str
) -> dict | None:
    await db.execute(
        """UPDATE entries SET is_resolved = 1, resolution_text = ?, updated_at = ?
           WHERE id = ?""",
        (resolution_text, datetime.utcnow().isoformat(), entry_id),
    )
    await db.commit()
    return await get_entry(db, entry_id)


async def delete_entry(db: aiosqlite.Connection, entry_id: int) -> bool:
    cursor = await db.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
    await db.commit()
    return cursor.rowcount > 0


async def count_entries(db: aiosqlite.Connection, user_id: int = 0) -> int:
    cursor = await db.execute(
        "SELECT COUNT(*) FROM entries WHERE user_id = ?", (user_id,)
    )
    row = await cursor.fetchone()
    return row[0]


def _row_to_dict(row: aiosqlite.Row) -> dict:
    d = dict(row)
    d["tags"] = json.loads(d.get("tags") or "[]")
    d["is_resolved"] = bool(d.get("is_resolved"))
    return d
