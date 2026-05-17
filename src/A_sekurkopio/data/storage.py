"""SQLite storage for A-sekurkopio using A.data.base."""

from __future__ import annotations

from pathlib import Path

from A.data.base import SQLiteDB, backup_db, health_check
from A.core.paths import data_dir


def get_db() -> SQLiteDB:
    """Get SQLiteDB instance for sekurkopio with health check and backup.

    Returns:
        SQLiteDB instance connected to sekurkopio.db in data_dir()
    """
    db_path = data_dir() / "sekurkopio.db"
    if not health_check(db_path):
        from A.data.base import repair_db as _repair
        _repair(db_path)
    backup_db(db_path)
    db = SQLiteDB(db_path)
    _init_schema(db)
    return db


def _init_schema(db: SQLiteDB) -> None:
    """Initialize database schema."""
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS historio (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            okazis_je  TEXT NOT NULL,
            ago        TEXT NOT NULL,
            detaloj    TEXT NOT NULL DEFAULT '{}'
        )
        """
    )

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS auto_strategio (
            id         INTEGER PRIMARY KEY CHECK (id = 1),
            dosierujo  TEXT NOT NULL,
            intervalo  INTEGER NOT NULL DEFAULT 60,
            nombro     INTEGER NOT NULL DEFAULT 5,
            aktiva     INTEGER NOT NULL DEFAULT 1
        )
        """
    )
