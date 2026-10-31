"""Runtime configuration, read once from the environment (and backend/.env if present)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    database_url: str
    secret: str
    llm_provider: str  # "anthropic" | "openai" | "none"
    anthropic_model: str
    openai_model: str
    cors_origins: tuple[str, ...]


def _detect_provider() -> str:
    explicit = os.getenv("ATHAR_LLM_PROVIDER", "").strip().lower()
    if explicit:
        return explicit
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    return "none"


@lru_cache
def get_settings() -> Settings:
    default_db = f"sqlite:///{BACKEND_DIR / 'data' / 'athar.db'}"
    return Settings(
        database_url=os.getenv("ATHAR_DATABASE_URL", default_db),
        secret=os.getenv("ATHAR_SECRET", "change-me-local-dev-only"),
        llm_provider=_detect_provider(),
        anthropic_model=os.getenv("ATHAR_ANTHROPIC_MODEL", "claude-opus-5-5"),
        openai_model=os.getenv("ATHAR_OPENAI_MODEL", "gpt-4.1-mini"),
        cors_origins=("http://localhost:5710", "http://127.0.0.1:5710"),
    )
