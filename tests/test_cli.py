"""Tests for A-sekurkopio CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Generator

import pytest
from typer.testing import CliRunner

from A_sekurkopio.cli import app


runner = CliRunner()


class TestEksporti:
    """Tests for eksporti command."""

    def test_eksporti_help(self) -> None:
        """Test eksporti command help text."""
        result = runner.invoke(app, ["eksporti", "--help"])
        assert result.exit_code == 0
        assert "eksporti" in result.output.lower() or "Export" in result.output

    def test_eksporti_invalid_format(self, tmp_path: Path) -> None:
        """Test eksporti with invalid format."""
        output_file = tmp_path / "backup.txt"
        result = runner.invoke(app, ["eksporti", str(output_file), "--formato", "tar"])
        assert result.exit_code != 0

    def test_eksporti_missing_file(self) -> None:
        """Test eksporti without required argument."""
        result = runner.invoke(app, ["eksporti"])
        assert result.exit_code != 0


class TestImporti:
    """Tests for importi command."""

    def test_importi_help(self) -> None:
        """Test importi command help text."""
        result = runner.invoke(app, ["importi", "--help"])
        assert result.exit_code == 0
        assert "importi" in result.output.lower() or "Import" in result.output

    def test_importi_missing_file(self) -> None:
        """Test importi without required argument."""
        result = runner.invoke(app, ["importi"])
        assert result.exit_code != 0

    def test_importi_nonexistent_file(self) -> None:
        """Test importi with non-existent file."""
        result = runner.invoke(app, ["importi", "/nonexistent/backup.7z"])
        assert result.exit_code != 0


class TestHistorio:
    """Tests for historio command."""

    def test_historio_help(self) -> None:
        """Test historio command help text."""
        result = runner.invoke(app, ["historio", "--help"])
        assert result.exit_code == 0


class TestAuto:
    """Tests for auto command."""

    def test_auto_help(self) -> None:
        """Test auto command help text."""
        result = runner.invoke(app, ["auto", "--help"])
        assert result.exit_code == 0
        assert "auto" in result.output.lower() or "backup" in result.output
