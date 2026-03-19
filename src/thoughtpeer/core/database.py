from __future__ import annotations

import aiosqlite

_DB_PATH = "thoughtpeer.db"
_conn: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    global _conn
    if _conn is None:
        _conn = await aiosqlite.connect(_DB_PATH)
        _conn.row_factory = aiosqlite.Row
        await _conn.execute("PRAGMA journal_mode=WAL")
        await _conn.execute("PRAGMA foreign_keys=ON")
    return _conn


async def close_db() -> None:
    global _conn
    if _conn:
        await _conn.close()
        _conn = None


async def init_db() -> None:
    db = await get_db()
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL DEFAULT 'local',
            text TEXT NOT NULL,
            mood TEXT CHECK(mood IN ('great','good','neutral','bad','terrible')),
            tags TEXT DEFAULT '[]',
            is_resolved INTEGER DEFAULT 0,
            resolution_text TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS insights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id INTEGER NOT NULL UNIQUE,
            problems TEXT DEFAULT '[]',
            emotions TEXT DEFAULT '[]',
            category TEXT,
            severity INTEGER DEFAULT 5,
            keywords TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (entry_id) REFERENCES entries(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS peer_pool (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anon_hash TEXT NOT NULL,
            category TEXT NOT NULL,
            tags TEXT DEFAULT '[]',
            keywords TEXT DEFAULT '[]',
            severity INTEGER DEFAULT 5,
            is_resolved INTEGER DEFAULT 0,
            resolution_text TEXT,
            mood TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_entries_user ON entries(user_id);
        CREATE INDEX IF NOT EXISTS idx_entries_mood ON entries(mood);
        CREATE INDEX IF NOT EXISTS idx_entries_created ON entries(created_at);
        CREATE INDEX IF NOT EXISTS idx_peer_category ON peer_pool(category);
        CREATE INDEX IF NOT EXISTS idx_peer_resolved ON peer_pool(is_resolved);
    """)
    await db.commit()
