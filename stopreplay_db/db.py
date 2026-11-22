"""Connection and migration helpers.

Credentials come only from the environment (DATABASE_URL). Nothing here invents
a connection string. For Supabase, use the project's pooled/connection URL.
"""
from __future__ import annotations

import os
import pathlib
from typing import Iterable

import psycopg
from psycopg.rows import dict_row

MIGRATIONS_DIR = pathlib.Path(__file__).resolve().parent.parent / "supabase" / "migrations"


def dsn(explicit: str | None = None) -> str:
    url = explicit or os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Point it at a local Postgres or the Supabase "
            "connection string (see .env.example). Credentials are never hard-coded."
        )
    return url


def connect(explicit: str | None = None, *, autocommit: bool = True) -> psycopg.Connection:
    return psycopg.connect(dsn(explicit), row_factory=dict_row, autocommit=autocommit)


def migration_files(directory: pathlib.Path = MIGRATIONS_DIR) -> list[pathlib.Path]:
    return sorted(directory.glob("*.sql"))


def apply_migrations(conn: psycopg.Connection, directory: pathlib.Path = MIGRATIONS_DIR) -> list[str]:
    applied: list[str] = []
    with conn.transaction():
        for path in migration_files(directory):
            conn.execute(path.read_text(encoding="utf-8"))
            applied.append(path.name)
    return applied


def reset_schema(conn: psycopg.Connection, directory: pathlib.Path = MIGRATIONS_DIR) -> list[str]:
    """Drop and recreate the public schema, then apply migrations. Test use only."""
    conn.execute("drop schema if exists public cascade; create schema public;")
    return apply_migrations(conn, directory)


def truncate_all(conn: psycopg.Connection, tables: Iterable[str] | None = None) -> None:
    """Fast per-test reset. TRUNCATE is allowed by the append-only guard."""
    names = list(tables) if tables else [
        "finding_evidence", "turns", "findings", "analysis_results",
        "events", "facts", "hooks", "sources",
    ]
    conn.execute("truncate " + ", ".join(names) + " cascade;")
