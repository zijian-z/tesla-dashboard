from __future__ import annotations

from collections.abc import Iterable, Mapping
from decimal import Decimal
from datetime import date, datetime
from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import get_settings

_pool: ConnectionPool | None = None


def _configure_connection(conn: Any) -> None:
    settings = get_settings()
    conn.execute("SET default_transaction_read_only = on")
    conn.execute(f"SET statement_timeout = {int(settings.statement_timeout_ms)}")


def init_pool() -> None:
    global _pool
    if _pool is not None:
        return

    settings = get_settings()
    _pool = ConnectionPool(
        conninfo=settings.database_url,
        min_size=settings.db_pool_min_size,
        max_size=settings.db_pool_max_size,
        kwargs={"row_factory": dict_row, "autocommit": True},
        configure=_configure_connection,
        open=False,
    )
    _pool.open(wait=True, timeout=15)


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def pool() -> ConnectionPool:
    if _pool is None:
        init_pool()
    assert _pool is not None
    return _pool


def fetch_all(sql: str, params: Iterable[Any] | Mapping[str, Any] = ()) -> list[dict[str, Any]]:
    with pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]


def fetch_one(sql: str, params: Iterable[Any] | Mapping[str, Any] = ()) -> dict[str, Any] | None:
    with pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else None


def clean_json(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, list):
        return [clean_json(item) for item in value]
    if isinstance(value, tuple):
        return [clean_json(item) for item in value]
    if isinstance(value, dict):
        return {key: clean_json(item) for key, item in value.items()}
    return value
