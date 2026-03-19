from __future__ import annotations

import json
from datetime import datetime

import aiosqlite


async def upsert_insight(
    db: aiosqlite.Connection, *, entry_id: int,
    problems: list[str], emotions: list[str], category: str | None,
    severity: int, keywords: list[str],
    summary: str = "", advice: str = "",
) -> dict:
    now = datetime.utcnow().isoformat()
    await db.execute(
        """INSERT INTO insights (entry_id, problems, emotions, category, severity, keywords, summary, advice, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(entry_id) DO UPDATE SET
             problems=excluded.problems, emotions=excluded.emotions,
             category=excluded.category, severity=excluded.severity,
             keywords=excluded.keywords, summary=excluded.summary,
             advice=excluded.advice, created_at=excluded.created_at""",
        (entry_id, json.dumps(problems), json.dumps(emotions), category,
         severity, json.dumps(keywords), summary, advice, now),
    )
    await db.commit()
    return await get_insight_by_entry(db, entry_id)


async def get_insight_by_entry(db: aiosqlite.Connection, entry_id: int) -> dict | None:
    cursor = await db.execute("SELECT * FROM insights WHERE entry_id = ?", (entry_id,))
    row = await cursor.fetchone()
    return _row_to_dict(row) if row else None


async def get_aggregated_patterns(db: aiosqlite.Connection, user_id: int = 0) -> dict:
    cursor = await db.execute(
        """SELECT i.* FROM insights i JOIN entries e ON i.entry_id = e.id
           WHERE e.user_id = ? ORDER BY i.created_at DESC""",
        (user_id,),
    )
    rows = await cursor.fetchall()
    insights = [_row_to_dict(r) for r in rows]

    problems: dict[str, int] = {}
    emotions: dict[str, int] = {}
    categories: dict[str, int] = {}
    for ins in insights:
        for p in ins["problems"]:
            problems[p] = problems.get(p, 0) + 1
        for e in ins["emotions"]:
            emotions[e] = emotions.get(e, 0) + 1
        if ins["category"]:
            categories[ins["category"]] = categories.get(ins["category"], 0) + 1

    def top(d: dict, n: int = 10) -> list[dict]:
        return [{"name": k, "count": v} for k, v in sorted(d.items(), key=lambda x: -x[1])[:n]]

    mood_cursor = await db.execute(
        """SELECT date(created_at) as d, mood, COUNT(*) as cnt
           FROM entries WHERE user_id = ? GROUP BY d, mood ORDER BY d""",
        (user_id,),
    )
    mood_rows = await mood_cursor.fetchall()

    resolved_cursor = await db.execute(
        "SELECT COUNT(*) FROM entries WHERE user_id = ? AND is_resolved = 1", (user_id,),
    )
    resolved = (await resolved_cursor.fetchone())[0]

    return {
        "top_problems": top(problems),
        "top_emotions": top(emotions),
        "top_categories": top(categories),
        "mood_trend": [dict(r) for r in mood_rows],
        "total_entries": len(insights),
        "resolved_count": resolved,
    }


def _row_to_dict(row: aiosqlite.Row) -> dict:
    d = dict(row)
    for field in ("problems", "emotions", "keywords"):
        d[field] = json.loads(d.get(field) or "[]")
    return d
