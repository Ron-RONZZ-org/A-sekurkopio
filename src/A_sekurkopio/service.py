"""Service layer for A-sekurkopio."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from A_sekurkopio.data.storage import get_db

_HISTORY_MAX = 5
_AUTO_INTERVAL_DEFAULT = 60
_AUTO_NOMBRO_DEFAULT = 5

_service = None


def get_service():
    """Get singleton service instance."""
    global _service
    if _service is None:
        _service = _SekurkopioService()
    return _service


class _SekurkopioService:
    """Backup and restore service."""

    def __init__(self):
        self.db = get_db()

    def push_history(self, ago: str, detaloj: dict | None = None) -> None:
        """Record a history entry, keeping at most _HISTORY_MAX rows."""
        now = datetime.now(timezone.utc).isoformat()
        self.db.execute(
            "INSERT INTO historio (okazis_je, ago, detaloj) VALUES (?, ?, ?)",
            (now, ago, json.dumps(detaloj or {})),
        )
        # Prune old entries
        self.db.execute(
            f"DELETE FROM historio WHERE id NOT IN "
            f"(SELECT id FROM historio ORDER BY id DESC LIMIT {_HISTORY_MAX})"
        )

    def load_history(self) -> list[dict]:
        """Load history entries."""
        return self.db.execute("SELECT * FROM historio ORDER BY id DESC")

    def load_auto_strategy(self) -> dict | None:
        """Load auto-backup strategy."""
        row = self.db.execute_one("SELECT * FROM auto_strategio WHERE id = 1")
        return dict(row) if row else None

    def save_auto_strategy(self, dosierujo: str, intervalo: int, nombro: int) -> None:
        """Save auto-backup strategy."""
        self.db.execute(
            """INSERT INTO auto_strategio (id, dosierujo, intervalo, nombro, aktiva)
               VALUES (1, ?, ?, ?, 1)
               ON CONFLICT(id) DO UPDATE
               SET dosierujo=excluded.dosierujo,
                   intervalo=excluded.intervalo,
                   nombro=excluded.nombro,
                   aktiva=1""",
            (dosierujo, intervalo, nombro),
        )

    def collect_data_files(self) -> list[Path]:
        """Collect A data files for backup via plugin discovery."""
        from A.core.backup_targets import get_backup_targets

        return [t.path for t in get_backup_targets() if t.path.exists()]
