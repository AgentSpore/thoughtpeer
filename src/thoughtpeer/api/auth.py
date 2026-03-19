from __future__ import annotations

from fastapi import APIRouter

from ..core.deps import DbDep, SettingsDep, UserDep
from ..schemas.user import UserLogin, UserRegister, UserUpdate, TokenResponse
from ..services import auth_service
from ..repositories import user_repo

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(data: UserRegister, db: DbDep, settings: SettingsDep):
    return await auth_service.register(
        db, settings,
        email=data.email, username=data.username,
        password=data.password, display_name=data.display_name,
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: DbDep, settings: SettingsDep):
    return await auth_service.login(db, settings, email=data.email, password=data.password)


@router.get("/me")
async def me(user: UserDep):
    return {
        "id": user["id"],
        "email": user["email"],
        "username": user["username"],
        "display_name": user.get("display_name"),
        "avatar_url": user.get("avatar_url"),
        "bio": user.get("bio"),
        "streak_days": user.get("streak_days", 0),
        "created_at": user.get("created_at", ""),
    }


@router.patch("/me")
async def update_me(data: UserUpdate, user: UserDep, db: DbDep):
    updated = await user_repo.update_user(db, user["id"], **data.model_dump(exclude_none=True))
    return {
        "id": updated["id"],
        "email": updated["email"],
        "username": updated["username"],
        "display_name": updated.get("display_name"),
        "avatar_url": updated.get("avatar_url"),
        "bio": updated.get("bio"),
        "streak_days": updated.get("streak_days", 0),
        "created_at": updated.get("created_at", ""),
    }
