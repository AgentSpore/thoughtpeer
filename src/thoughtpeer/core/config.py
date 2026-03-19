from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "ThoughtPeer"
    debug: bool = False
    database_url: str = "sqlite+aiosqlite:///./thoughtpeer.db"
    host: str = "0.0.0.0"
    port: int = 8000

    # Peer matching
    similarity_threshold: float = 0.35
    max_peer_results: int = 10

    # Privacy
    min_entries_for_sharing: int = 3  # user must have N entries before sharing

    model_config = {"env_prefix": "TP_", "env_file": ".env"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
