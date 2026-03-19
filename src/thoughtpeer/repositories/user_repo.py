from __future__ import annotations

import hashlib
import hmac
import os
from datetime import datetime

import aiosqlite


def _hash_password(password: str) -> str:
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    return salt.hex() + ':' + key.hex()


def _verify_password(password: str, stored: str) -> bool:
    salt_hex, key_hex = stored.split(':')
    salt = bytes.fromhex(salt_hex)
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    return hmac.compare_digest(key, bytes.fromhex(key_hex))


async def create_user(
    db: aiosqlite.Connection, *, email: str, username: str,
    password: str, display_name: str | None = None,
) -> dict:
    password_hash = _hash_password(password)
    now = datetime.utcnow().isoformat()
    cursor = await db.execute(
        """INSERT INTO users (email, username, password_hash, display_name, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (email, username, password_hash, display_name or username, now, now),
    )
    await db.commit()
    return await get_user_by_id(db, cursor.lastrowid)


async def get_user_by_id(db: aiosqlite.Connection, user_id: int) -> dict | None:
    cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_user_by_email(db: aiosqlite.Connection, email: str) -> dict | None:
    cursor = await db.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_user_by_username(db: aiosqlite.Connection, username: str) -> dict | None:
    cursor = await db.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def verify_password(password: str, password_hash: str) -> bool:
    return _verify_password(password, password_hash)


async def update_user(db: aiosqlite.Connection, user_id: int, **fields) -> dict | None:
    sets, params = [], []
    for key, val in fields.items():
        if val is not None:
            sets.append(f"{key} = ?")
            params.append(val)
    if not sets:
        return await get_user_by_id(db, user_id)
    sets.append("updated_at = ?")
    params.append(datetime.utcnow().isoformat())
    params.append(user_id)
    await db.execute(f"UPDATE users SET {', '.join(sets)} WHERE id = ?", params)
    await db.commit()
    return await get_user_by_id(db, user_id)


async def update_streak(db: aiosqlite.Connection, user_id: int) -> None:
    user = await get_user_by_id(db, user_id)
    if not user:
        return
    today = datetime.utcnow().strftime("%Y-%m-%d")
    last = user.get("last_entry_date")
    if last == today:
        return
    yesterday = datetime.utcnow().date().toordinal() - 1
    if last:
        last_ord = datetime.strptime(last, "%Y-%m-%d").date().toordinal()
        streak = (user.get("streak_days") or 0) + 1 if last_ord == yesterday else 1
    else:
        streak = 1
    await db.execute(
        "UPDATE users SET streak_days = ?, last_entry_date = ? WHERE id = ?",
        (streak, today, user_id),
    )
    await db.commit()
