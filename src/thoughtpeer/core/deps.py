from __future__ import annotations

from typing import Annotated

import aiosqlite
import jwt
from fastapi import Depends, HTTPException, Header

from .config import Settings, get_settings
from .database import get_db

DbDep = Annotated[aiosqlite.Connection, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


async def get_current_user(
    authorization: str = Header(...),
    db: aiosqlite.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid authorization header")
    token = authorization[7:]
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(401, "Invalid token payload")

    cursor = await db.execute("SELECT * FROM users WHERE id = ?", (int(user_id),))
    user = await cursor.fetchone()
    if not user:
        raise HTTPException(401, "User not found")
    return dict(user)


UserDep = Annotated[dict, Depends(get_current_user)]
