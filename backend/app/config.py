from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    app_name: str
    database_url: str
    statement_timeout_ms: int
    db_pool_min_size: int
    db_pool_max_size: int
    cors_origins: tuple[str, ...]


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return int(raw)


def _csv_env(name: str) -> tuple[str, ...]:
    raw = os.getenv(name, "")
    return tuple(item.strip() for item in raw.split(",") if item.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "TeslaMate Dashboard API"),
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql://teslamate:teslamate@database:5432/teslamate",
        ),
        statement_timeout_ms=_int_env("STATEMENT_TIMEOUT_MS", 15000),
        db_pool_min_size=_int_env("DB_POOL_MIN_SIZE", 1),
        db_pool_max_size=_int_env("DB_POOL_MAX_SIZE", 5),
        cors_origins=_csv_env("CORS_ORIGINS"),
    )
