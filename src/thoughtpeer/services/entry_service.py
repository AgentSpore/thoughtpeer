from __future__ import annotations

import aiosqlite
from fastapi import HTTPException

from ..repositories import entry_repo, user_repo
from ..schemas.entry import EntryCreate, EntryUpdate


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


async def resolve(db: aiosqlite.Connection, entry_id: int, user_id: int, resolution_text: str) -> dict:
    await get(db, entry_id, user_id)
    return await entry_repo.resolve_entry(db, entry_id, resolution_text)


async def delete(db: aiosqlite.Connection, entry_id: int, user_id: int) -> None:
    await get(db, entry_id, user_id)
    await entry_repo.delete_entry(db, entry_id)
