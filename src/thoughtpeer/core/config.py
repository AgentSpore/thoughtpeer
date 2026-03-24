from __future__ import annotations

import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "ThoughtPeer"
    debug: bool = False
    database_url: str = "sqlite+aiosqlite:///./thoughtpeer.db"
    host: str = "0.0.0.0"
    port: int = 8000

    # Auth
    jwt_secret: str = "change-me-in-production-thoughtpeer-secret-2024"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 72

    # LLM (OpenRouter - free models only)
    openrouter_api_key: str = ""
    llm_model: str = "google/gemini-2.0-flash-001"

    # Peer matching
    similarity_threshold: float = 0.35
    max_peer_results: int = 10

    model_config = {"env_prefix": "TP_", "env_file": ".env"}


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    # Fallback: use OPENROUTER_API_KEY if TP_OPENROUTER_API_KEY not set
    if not s.openrouter_api_key:
        s.openrouter_api_key = os.environ.get("OPENROUTER_API_KEY", "")
    return s
