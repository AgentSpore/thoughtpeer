from __future__ import annotations

from datetime import datetime, timedelta

import jwt
from fastapi import HTTPException

import aiosqlite

from ..core.config import Settings
from ..repositories import user_repo


async def register(db: aiosqlite.Connection, settings: Settings, *, email: str, username: str, password: str, display_name: str | None) -> dict:
    existing = await user_repo.get_user_by_email(db, email)
    if existing:
        raise HTTPException(409, "Email already registered")
    existing = await user_repo.get_user_by_username(db, username)
    if existing:
        raise HTTPException(409, "Username already taken")

    user = await user_repo.create_user(db, email=email, username=username, password=password, display_name=display_name)
    token = _create_token(user["id"], settings)
    return {"access_token": token, "token_type": "bearer", "user": _user_response(user)}


async def login(db: aiosqlite.Connection, settings: Settings, *, email: str, password: str) -> dict:
    user = await user_repo.get_user_by_email(db, email)
    if not user:
        raise HTTPException(401, "Invalid email or password")
    if not await user_repo.verify_password(password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    token = _create_token(user["id"], settings)
    return {"access_token": token, "token_type": "bearer", "user": _user_response(user)}


def _create_token(user_id: int, settings: Settings) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.utcnow() + timedelta(hours=settings.jwt_expire_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _user_response(user: dict) -> dict:
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
