"""Tests for A-sekurkopio storage layer."""

from __future__ import annotations

import pytest


class TestStorage:
    """Tests for database connection management."""

    def test_get_db_creates_tables(self):
        """Verify get_db() creates required tables."""
        from A_sekurkopio.data.storage import get_db

        db = get_db()
        tables = {r["name"] for r in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        assert "historio" in tables
        assert "auto_strategio" in tables

    def test_get_db_is_singleton(self):
        """Verify get_db() returns the same instance on repeated calls."""
        from A_sekurkopio.data.storage import get_db

        db1 = get_db()
        db2 = get_db()
        assert db1 is db2

    def test_wal_mode_enabled(self):
        """Verify WAL journal mode is active."""
        from A_sekurkopio.data.storage import get_db

        db = get_db()
        result = db.execute_one("PRAGMA journal_mode")
        assert result is not None
        assert "wal" in str(result.get("journal_mode", "")).lower()
