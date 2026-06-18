"""CLI commands for A-sekurkopio."""

from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.table import Table

from A import error, info, tr_multi

from A_sekurkopio.service import get_service

from A_sekurkopio.export_cmd import cmd_eksporti
from A_sekurkopio.import_cmd import cmd_importi
from A_sekurkopio.auto_cmd import cmd_auto, cmd_daemon
from A_sekurkopio.install_cmd import cmd_install_systemd, cmd_install_cron

app = typer.Typer(
    name="sekurkopio",
    help=tr_multi(
        "sekurkopio — sekurkopii kaj restauxri datumojn.",
        "sekurkopio — backup and restore data.",
        "sekurkopio — sauvegarder et restaurer les donnees.",
    ),
    no_args_is_help=True,
)

console = Console()
_service = get_service()

_HISTORY_MAX = 5


@app.command("historio")
def historio_cmd() -> None:
    """Montri resumon de la lastaj 5 sekurkopio-operacioj."""
    entries = _service.load_history()
    if not entries:
        info(
            tr_multi(
                "Neniu historio trovita.",
                "No history found.",
                "Aucun historique trouve.",
            )
        )
        return

    table = Table(
        title=tr_multi(
            f"Historio (lastaj {_HISTORY_MAX})",
            f"History (last {_HISTORY_MAX})",
            f"Historique (derniers {_HISTORY_MAX})",
        )
    )
    table.add_column("#")
    table.add_column(
        tr_multi("Okazis", "Occurred", "Survenu"), style="cyan"
    )
    table.add_column(tr_multi("Ago", "Action", "Action"))
    table.add_column(tr_multi("Detaloj", "Details", "Details"))

    for i, entry in enumerate(entries, 1):
        ts = entry["okazis_je"][:19].replace("T", " ")
        detaloj = json.loads(entry["detaloj"])
        detail_str = ", ".join(f"{k}={v}" for k, v in detaloj.items())
        table.add_row(str(i), ts, entry["ago"], detail_str)

    console.print(table)


# ──────────────────────────────────────────────────────────────────────────────
# Register extracted commands
# ──────────────────────────────────────────────────────────────────────────────

app.command(name="eksporti")(cmd_eksporti)
app.command(name="importi")(cmd_importi)
app.command(name="auto")(cmd_auto)
app.command(name="daemon")(cmd_daemon)
app.command(name="install-systemd")(cmd_install_systemd)
app.command(name="install-cron")(cmd_install_cron)


__all__ = ["app"]
