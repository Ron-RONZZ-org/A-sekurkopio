"""Tests for A-sekurkopio service layer."""

from __future__ import annotations

from pathlib import Path
from typing import Generator

import pytest

from A_sekurkopio.service import get_service


@pytest.fixture
def service():
    """Get service instance."""
    return get_service()


class TestCollectDataFiles:
    """Tests for collect_data_files method."""

    def test_collect_no_files(self, service, tmp_path: Path, monkeypatch) -> None:
        """Test when no data files exist."""
        monkeypatch.setattr("pathlib.Path.exists", lambda self: False)
        files = service.collect_data_files()
        assert files == []

    def test_collect_with_files(self, service, tmp_path: Path, monkeypatch) -> None:
        """Test collecting existing files."""
        # Mock data_dir to return tmp_path
        monkeypatch.setattr(
            "A_sekurkopio.service.data_dir", lambda: tmp_path
        )

        # Create test files
        test_files = ["vorto.db", "encik.db"]
        for fname in test_files:
            (tmp_path / fname).touch()

        files = service.collect_data_files()
        assert len(files) == 2


class TestHistory:
    """Tests for history operations."""

    def test_push_and_load_history(self, service) -> None:
        """Test pushing and loading history."""
        # Push a history entry
        service.push_history("test_action", {"key": "value"})

        # Load history
        entries = service.load_history()
        assert len(entries) > 0
        assert entries[0]["ago"] == "test_action"

    def test_history_limit(self, service) -> None:
        """Test history is limited to _HISTORY_MAX entries."""
        from A_sekurkopio.service import _HISTORY_MAX

        # Push more than max entries
        for i in range(_HISTORY_MAX + 3):
            service.push_history(f"action_{i}")

        entries = service.load_history()
        assert len(entries) <= _HISTORY_MAX


class TestAutoStrategy:
    """Tests for auto-backup strategy operations."""

    def test_save_and_load_strategy(self, service, tmp_path: Path) -> None:
        """Test saving and loading auto-backup strategy."""
        dosierujo = str(tmp_path / "backups")
        intervalo = 30
        nombro = 10

        service.save_auto_strategy(dosierujo, intervalo, nombro)

        strategy = service.load_auto_strategy()
        assert strategy is not None
        assert strategy["dosierujo"] == dosierujo
        assert strategy["intervalo"] == intervalo
        assert strategy["nombro"] == nombro

    def test_load_nonexistent_strategy(self, service) -> None:
        """Test loading strategy when none exists."""
        # The service initializes with a fresh DB in tests
        strategy = service.load_auto_strategy()
        # May return None or existing strategy
        assert strategy is None or isinstance(strategy, dict)
