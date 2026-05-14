"""Shared pytest fixtures — deterministic DB lifecycle for SQLite-backed tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy.pool import NullPool
from sqlmodel import create_engine

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

    from sqlalchemy.engine import Engine

from update_guardian.config import Settings
from update_guardian.core.storage import StorageService


def _sqlite_test_engine(url: str, *, connect_args: dict[str, object]) -> Engine:
    """Test engines use NullPool so each checkout returns a fresh, fully-closed SQLite connection.

    Avoids ResourceWarning from pooled DBAPI connections + WAL handles lingering after ``dispose()``
    on some platforms (especially when tests open multiple sessions against the same file URL).
    """
    return create_engine(url, connect_args=connect_args, poolclass=NullPool)


@pytest.fixture(name="storage")
def _storage_fixture(tmp_path: Path) -> Generator[StorageService, None, None]:
    """Fresh SQLite database per test; engine disposed after teardown (no pooled leaks)."""
    db_path = tmp_path / "guardian_test.db"
    settings = Settings(database_url=f"sqlite:///{db_path.as_posix()}")
    svc = StorageService(settings=settings, engine_factory=_sqlite_test_engine)
    svc.init_db()
    try:
        yield svc
    finally:
        svc.dispose()
