"""Restaurigi (restore) command for A-sekurkopio.

Restores a module's database from a timestamped backup stored in
``~/.local/share/A/.backups/{module}/{timestamp}.db``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from A import error, info, tr_multi
from A.core.backup import (
    list_backups,
    restore_latest,
    restore_by_timestamp,
)
from A.core.paths import data_dir

console = Console()


def cmd_restaurigi(
    module: str = typer.Argument(
        ...,
        help=tr_multi(
            "Modula nomo (ekz. A-semantika)",
            "Module name (e.g. A-semantika)",
            "Nom du module (ex. A-semantika)",
        ),
    ),
    timestamp: str = typer.Argument(
        "",
        help=tr_multi(
            "Tempmarko de sekurkopio (montru liston se malplena)",
            "Backup timestamp (show list if empty)",
            "Horodatage de la sauvegarde (afficher la liste si vide)",
        ),
    ),
    jes: bool = typer.Option(
        False, "-y", "--jes", "--yes",
        help=tr_multi(
            "Preterpasi konfirmon",
            "Skip confirmation",
            "Ignorer la confirmation",
        ),
    ),
) -> None:
    """Restaurigi datumojn de sekurkopio.

    Restores a module's database from a timestamped backup.  If no timestamp
    is given, lists available backups and exits.

    Examples::

        A sekurkopio restaurigi A-semantika              # list backups
        A sekurkopio restaurigi A-semantika 20260615T125705780168106
    """
    backups = list_backups(module)
    if not backups:
        error(tr_multi(
            "Neniuj sekurkopioj por {m}.",
            "No backups for {m}.",
            "Aucune sauvegarde pour {m}.",
        ).format(m=module))
        raise typer.Exit(1)

    if not timestamp:
        # Show backup list
        table = Table(
            title=tr_multi(
                f"Sekurkopioj por {module}",
                f"Backups for {module}",
                f"Sauvegardes pour {module}",
            ),
            show_header=True,
        )
        table.add_column("#")
        table.add_column(tr_multi("Tempmarko", "Timestamp", "Horodatage"))
        table.add_column(tr_multi("Grando", "Size", "Taille"))
        table.add_column(tr_multi("Ago", "Age", "Âge"))

        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        for i, b in enumerate(backups, 1):
            ts = b["timestamp"]
            sz = b["size_bytes"]
            # Human-readable size
            if sz > 1_000_000:
                size_str = f"{sz / 1_000_000:.1f} MB"
            elif sz > 1_000:
                size_str = f"{sz / 1_000:.1f} KB"
            else:
                size_str = f"{sz} B"
            # Age
            try:
                dt = datetime.strptime(ts[:19], "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
                age_days = (now - dt).days
                age_str = f"{age_days}d" if age_days > 0 else "< 1d"
            except (ValueError, IndexError):
                age_str = "?"
            table.add_row(str(i), ts, size_str, age_str)

        console.print(table)
        info(tr_multi(
            "Uzu: A sekurkopio restaurigi {m} TEMPMARKO",
            "Usage: A sekurkopio restaurigi {m} TIMESTAMP",
            "Utilisation : A sekurkopio restaurigi {m} HORODATAGE",
        ).format(m=module))
        return

    # Confirm restore
    target_path = data_dir() / module / f"{module.lower().replace('-', '_')}.db"
    if not target_path.exists():
        # Try to find the DB file in various possible locations
        candidates = list(data_dir().rglob(f"{module.lower().replace('-', '_')}.db"))
        if candidates:
            target_path = candidates[0]
        else:
            error(tr_multi(
                "Ne povis trovi datumbazon por {m} en {d}",
                "Could not find database for {m} in {d}",
                "Impossible de trouver la base de données pour {m} dans {d}",
            ).format(m=module, d=data_dir()))
            raise typer.Exit(1)

    if not jes:
        from A.utils.interactive import confirm_action

        info(tr_multi(
            "Restarigos {m} de sekurkopio {ts} → {path}",
            "Will restore {m} from backup {ts} → {path}",
            "Va restaurer {m} depuis la sauvegarde {ts} → {path}",
        ).format(m=module, ts=timestamp, path=target_path))

        if not confirm_action(
            tr_multi(
                "Ĉu daŭrigi?",
                "Continue?",
                "Continuer ?",
            ),
            default=False,
        ):
            info(tr_multi("Nuligita.", "Cancelled.", "Annulé."))
            raise typer.Exit(0)

    try:
        restore_by_timestamp(module, timestamp, target_path)
    except FileNotFoundError:
        error(tr_multi(
            "Neniu sekurkopio trovita: {m} {ts}",
            "No backup found: {m} {ts}",
            "Aucune sauvegarde trouvée : {m} {ts}",
        ).format(m=module, ts=timestamp))
        raise typer.Exit(1) from None

    info(tr_multi(
        "Restarigis {m} de sekurkopio {ts}",
        "Restored {m} from backup {ts}",
        "Restauré {m} depuis la sauvegarde {ts}",
    ).format(m=module, ts=timestamp))
