"""Shared pytest fixtures — deterministic DB lifecycle for SQLite-backed tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

from update_guardian.config import Settings
from update_guardian.core.storage import StorageService, reset_storage_singleton


@pytest.fixture(name="storage")
def _storage_fixture(tmp_path: Path) -> Generator[StorageService, None, None]:
    """Fresh SQLite database per test; engine disposed after teardown (no pooled leaks)."""
    reset_storage_singleton()
    db_path = tmp_path / "guardian_test.db"
    settings = Settings(database_url=f"sqlite:///{db_path.as_posix()}")
    svc = StorageService(settings=settings)
    svc.init_db()
    try:
        yield svc
    finally:
        svc.dispose()
