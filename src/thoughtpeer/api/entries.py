from __future__ import annotations

from fastapi import APIRouter, Query

from ..core.deps import DbDep, UserDep
from ..repositories import insight_repo
from ..schemas.entry import EntryCreate, EntryResolve, EntryResponse, EntryUpdate, Mood
from ..services import entry_service
from ..services.ai_service import analyze_entry

router = APIRouter(prefix="/entries", tags=["entries"])


@router.post("", response_model=EntryResponse, status_code=201)
async def create_entry(data: EntryCreate, db: DbDep, user: UserDep):
    return await entry_service.create(db, user["id"], data)


@router.get("", response_model=list[EntryResponse])
async def list_entries(
    db: DbDep, user: UserDep,
    mood: Mood | None = None,
    tag: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    resolved: bool | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    return await entry_service.list_all(
        db, user["id"],
        mood=mood and mood.value, tag=tag,
        date_from=date_from, date_to=date_to,
        resolved=resolved, limit=limit, offset=offset,
    )


@router.get("/{entry_id}", response_model=EntryResponse)
async def get_entry(entry_id: int, db: DbDep, user: UserDep):
    return await entry_service.get(db, entry_id, user["id"])


@router.patch("/{entry_id}", response_model=EntryResponse)
async def update_entry(entry_id: int, data: EntryUpdate, db: DbDep, user: UserDep):
    return await entry_service.update(db, entry_id, user["id"], data)


@router.delete("/{entry_id}", status_code=204)
async def delete_entry(entry_id: int, db: DbDep, user: UserDep):
    await entry_service.delete(db, entry_id, user["id"])


@router.post("/{entry_id}/resolve", response_model=EntryResponse)
async def resolve_entry(entry_id: int, data: EntryResolve, db: DbDep, user: UserDep):
    return await entry_service.resolve(db, entry_id, user["id"], data.resolution_text)


@router.post("/{entry_id}/analyze")
async def analyze_entry_endpoint(entry_id: int, db: DbDep, user: UserDep):
    entry = await entry_service.get(db, entry_id, user["id"])
    analysis = await analyze_entry(entry["text"], entry.get("mood"))
    insight = await insight_repo.upsert_insight(
        db, entry_id=entry_id,
        problems=analysis["problems"],
        emotions=analysis["emotions"],
        category=analysis["category"],
        severity=analysis["severity"],
        keywords=analysis["keywords"],
        summary=analysis.get("summary", ""),
        advice=analysis.get("advice", ""),
    )
    return insight
