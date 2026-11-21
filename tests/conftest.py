"""Test fixtures. These run against a REAL Postgres named by DATABASE_URL.

The session fixture DROPS and recreates the public schema, so DATABASE_URL must
point at a throwaway/local database, never a shared or production one. When
DATABASE_URL is unset, every test skips (integration remains blocked, not green).
"""
from __future__ import annotations

import os

import pytest

from stopreplay_db import Storage, db

DSN = os.environ.get("DATABASE_URL")


@pytest.fixture(scope="session")
def conn():
    if not DSN:
        pytest.skip("DATABASE_URL not set; database integration tests are blocked.")
    connection = db.connect()
    db.reset_schema(connection)
    yield connection
    connection.close()


@pytest.fixture
def storage(conn):
    db.truncate_all(conn)
    return Storage(conn)
