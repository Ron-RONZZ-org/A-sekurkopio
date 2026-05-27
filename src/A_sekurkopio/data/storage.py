"""SQLite storage for A-sekurkopio using A.data.base."""

from __future__ import annotations

from pathlib import Path

from A.data.base import SQLiteDB, backup_db, health_check
from A.core.backup_targets import BackupTarget
from A.core.paths import data_dir

_db_instance: SQLiteDB | None = None


def get_db() -> SQLiteDB:
    """Get or create the shared database connection (singleton).

    All callers within the same process share one ``SQLiteDB`` instance,
    which uses one cached SQLite connection. This avoids WAL/SHM conflicts
    that occur when multiple connections access the same database file.

    The connection is lazily created on first call and cached in
    ``_db_instance``. Tests can reset the singleton by setting
    ``A_sekurkopio.data.storage._db_instance = None`` in their teardown.

    Returns:
        SQLiteDB instance connected to sekurkopio.db in data_dir()
    """
    global _db_instance
    if _db_instance is not None:
        return _db_instance

    db_path = data_dir() / "sekurkopio.db"
    if not health_check(db_path):
        from A.data.base import repair_db as _repair
        _repair(db_path)
    backup_db(db_path)
    db = SQLiteDB(db_path)
    _init_schema(db)
    _db_instance = db
    return db


def get_backup_targets() -> list[BackupTarget]:
    """Return backup targets for A-sekurkopio."""
    return [
        BackupTarget(
            path=data_dir() / "sekurkopio.db",
            category="data",
            module="sekurkopio",
            label="Sekurkopio database",
        ),
    ]


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
