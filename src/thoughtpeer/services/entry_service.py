from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime

import aiosqlite
from fastapi import HTTPException

from ..core.config import get_settings
from ..repositories import entry_repo, insight_repo, peer_repo, user_repo
from ..schemas.entry import EntryCreate, EntryUpdate

_EXPORT_VERSION = 1


async def create(db: aiosqlite.Connection, user_id: int, data: EntryCreate) -> dict:
    entry = await entry_repo.create_entry(
        db, user_id=user_id, text=data.text, mood=data.mood.value, tags=data.tags
    )
    await user_repo.update_streak(db, user_id)
    return entry


async def get(db: aiosqlite.Connection, entry_id: int, user_id: int) -> dict:
    entry = await entry_repo.get_entry(db, entry_id)
    if not entry:
        raise HTTPException(404, "Entry not found")
    if int(entry["user_id"]) != user_id:
        raise HTTPException(403, "Not your entry")
    return entry


async def list_all(db: aiosqlite.Connection, user_id: int, **filters) -> list[dict]:
    return await entry_repo.list_entries(db, user_id=user_id, **filters)


async def update(db: aiosqlite.Connection, entry_id: int, user_id: int, data: EntryUpdate) -> dict:
    await get(db, entry_id, user_id)
    fields = data.model_dump(exclude_none=True)
    if "mood" in fields:
        fields["mood"] = fields["mood"].value
    return await entry_repo.update_entry(db, entry_id, **fields)


async def resolve(
    db: aiosqlite.Connection, entry_id: int, user_id: int,
    resolution_text: str, *, share_to_pool: bool = False,
) -> dict:
    entry = await get(db, entry_id, user_id)
    resolved = await entry_repo.resolve_entry(db, entry_id, resolution_text)
    if share_to_pool:
        insight = await insight_repo.get_insight_by_entry(db, entry_id)
        await peer_repo.add_to_pool(
            db, user_id=user_id,
            category=(insight or {}).get("category") or "general",
            tags=entry.get("tags") or [],
            keywords=(insight or {}).get("keywords") or [],
            severity=(insight or {}).get("severity") or 5,
            mood=entry.get("mood"),
            is_resolved=True,
            resolution_text=resolution_text,
        )
    return resolved


async def delete(db: aiosqlite.Connection, entry_id: int, user_id: int) -> None:
    await get(db, entry_id, user_id)
    await entry_repo.delete_entry(db, entry_id)


# ---- Export / Import ---------------------------------------------------------

def _sign(payload: str) -> str:
    settings = get_settings()
    return hmac.new(
        settings.jwt_secret.encode(), payload.encode(), hashlib.sha256,
    ).hexdigest()


async def export_all(db: aiosqlite.Connection, user_id: int) -> dict:
    rows = await entry_repo.list_entries(db, user_id=user_id, limit=10000, offset=0)
    entries = [
        {
            "original_id": r["id"],
            "text": r["text"],
            "mood": r["mood"],
            "tags": r["tags"],
            "is_resolved": r["is_resolved"],
            "resolution_text": r.get("resolution_text"),
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        }
        for r in rows
    ]
    payload = {
        "version": _EXPORT_VERSION,
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "user_id": user_id,
        "entries": entries,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload["signature"] = _sign(raw)
    return payload


async def import_dump(
    db: aiosqlite.Connection, user_id: int, raw: bytes,
) -> dict:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("invalid json") from exc
    if not isinstance(parsed, dict) or "entries" not in parsed:
        raise ValueError("missing entries")

    signature = parsed.pop("signature", None)
    integrity_ok = False
    if signature:
        expected = _sign(json.dumps(parsed, sort_keys=True, separators=(",", ":")))
        integrity_ok = hmac.compare_digest(signature, expected)

    existing = await entry_repo.list_entries(db, user_id=user_id, limit=10000, offset=0)
    # Dedupe key: (created_at, first 80 chars of text) — stable across exports.
    seen = {(e["created_at"], e["text"][:80]) for e in existing}

    imported = 0
    skipped = 0
    for item in parsed.get("entries", []):
        if not isinstance(item, dict) or "text" not in item:
            skipped += 1
            continue
        key = (item.get("created_at", ""), (item.get("text") or "")[:80])
        if key in seen:
            skipped += 1
            continue
        mood = item.get("mood") or "neutral"
        if mood not in {"great", "good", "neutral", "bad", "terrible"}:
            mood = "neutral"
        entry = await entry_repo.create_entry(
            db, user_id=user_id, text=item["text"][:10000],
            mood=mood, tags=list(item.get("tags") or []),
        )
        if item.get("is_resolved") and item.get("resolution_text"):
            await entry_repo.resolve_entry(db, entry["id"], item["resolution_text"])
        imported += 1

    return {
        "imported": imported,
        "skipped": skipped,
        "integrity_verified": integrity_ok,
    }
