"""Auto backup and daemon commands for A-sekurkopio."""

from __future__ import annotations

import signal
import time
from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from A import error, info, tr_multi
from A.core.paths import data_dir

from A_sekurkopio.service import get_service

console = Console()
_service = get_service()

_HISTORY_MAX = 5
_AUTO_INTERVAL_DEFAULT = 60
_AUTO_NOMBRO_DEFAULT = 5


def _log_error(fh, message: str) -> None:
    """Log error message to file if file handle is open."""
    if fh:
        try:
            ts = datetime.now(timezone.utc).isoformat()
            fh.write(f"{ts} [ERROR] {message}\n")
            fh.flush()
        except OSError:
            pass


def _do_auto_backup(dosierujo: Path, pasvorto: str, nombro: int) -> Path:
    """Create one auto-backup file. Returns the path created."""
    if nombro < 1:
        raise ValueError(
            f"nombro ({nombro}) devas esti almenaŭ 1. "
            f"Korektu vian strategion per: sekurkopio auto --nombro N"
        )

    try:
        import py7zr
    except ImportError:
        raise ImportError(
            "py7zr is required for 7z backup. Install with: "
            "uv pip install A-sekurkopio[backup]"
        )

    dosierujo.mkdir(parents=True, exist_ok=True)

    try:
        files = sorted(
            dosierujo.glob("A_backup_*.7z"),
            key=lambda p: p.stat().st_mtime,
        )
    except OSError as e:
        raise OSError(
            f"Ne povas legi dosierujon {dosierujo}: {e}"
        ) from e

    while len(files) >= nombro:
        try:
            files[0].unlink()
        except OSError as e:
            raise OSError(
                f"Ne povas forigi malnovan kopion {files[0]}: {e}"
            ) from e
        files = files[1:]

    now_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out = dosierujo / f"A_backup_{now_str}.7z"

    files = _service.collect_data_files()
    if not files:
        raise ValueError("Neniuj datumoj por sekurkopio.")

    with py7zr.SevenZipFile(str(out), "w", password=pasvorto) as szf:
        for fp in files:
            szf.write(fp, fp.name)

    return out


def cmd_auto(
    dosierujo: str | None = None,
    intervalo: int | None = None,
    nombro: int | None = None,
) -> None:
    """Manage automatic periodic backups."""
    strategy = _service.load_auto_strategy()

    if dosierujo is None and intervalo is None and nombro is None:
        if not strategy:
            info(
                tr_multi(
                    "Neniu axtomata sekurkopio konfigurita.",
                    "No automatic backup configured.",
                    "Aucune sauvegarde automatique configuree.",
                )
            )
            return

        table = Table(
            title=tr_multi(
                "Axtomata sekurkopio-strategio",
                "Automatic backup strategy",
                "Strategie de sauvegarde automatique",
            )
        )
        table.add_column(
            tr_multi("Kampo", "Field", "Champ"), style="cyan"
        )
        table.add_column(
            tr_multi("Valoro", "Value", "Valeur")
        )
        table.add_row(
            tr_multi("Dosierujo", "Directory", "Repertoire"),
            strategy["dosierujo"],
        )
        table.add_row(
            tr_multi("Intervalo", "Interval", "Intervalle"),
            f"{strategy['intervalo']} min",
        )
        table.add_row(
            tr_multi("Maks. kopioj", "Max copies", "Max copies"),
            str(strategy["nombro"]),
        )
        table.add_row(
            tr_multi("Aktiva", "Active", "Actif"),
            tr_multi("jes", "yes", "oui")
            if strategy["aktiva"]
            else tr_multi("ne", "no", "non"),
        )
        console.print(table)
        return

    new_dir = dosierujo or (
        strategy["dosierujo"]
        if strategy
        else str(data_dir() / "sekurkopioj")
    )
    new_intervalo = (
        intervalo
        if intervalo is not None
        else (strategy["intervalo"] if strategy else _AUTO_INTERVAL_DEFAULT)
    )
    new_nombro = (
        nombro
        if nombro is not None
        else (strategy["nombro"] if strategy else _AUTO_NOMBRO_DEFAULT)
    )

    _service.save_auto_strategy(new_dir, new_intervalo, new_nombro)
    Path(new_dir).mkdir(parents=True, exist_ok=True)

    info(
        tr_multi(
            f"Axtomata sekurkopio agordita:\n  Dosierujo : {new_dir}\n  Intervalo : {new_intervalo} min\n  Maks. kopioj: {new_nombro}",
            f"Automatic backup configured:\n  Directory : {new_dir}\n  Interval : {new_intervalo} min\n  Max copies: {new_nombro}",
            f"Sauvegarde automatique configuree:\n  Repertoire : {new_dir}\n  Intervalle : {new_intervalo} min\n  Max copies: {new_nombro}",
        )
    )


def cmd_daemon(
    pasvorto_dosiero: str | None = None,
    unufoje: bool = False,
    log_dosiero: str | None = None,
) -> None:
    """Run the automatic backup daemon."""
    strategy = _service.load_auto_strategy()
    if not strategy or not strategy.get("aktiva"):
        error(
            tr_multi(
                "Neniu aktiva axtomata strategio.\nRulu: sekurkopio auto [dosierujo]",
                "No active automatic strategy.\nRun: sekurkopio auto [directory]",
                "Aucune strategie active.\nExecution: sekurkopio auto [repertoire]",
            )
        )
        raise typer.Exit(1)

    if not pasvorto_dosiero:
        error(
            tr_multi(
                "--pasvorto-dosiero estas deviga por daemono.",
                "--pasvorto-dosiero is required for daemon.",
                "--pasvorto-dosiero est requis pour le daemon.",
            )
        )
        raise typer.Exit(1)

    pw_path = Path(pasvorto_dosiero).expanduser()
    if pw_path.is_dir():
        pw_path = pw_path / "backup_password.txt"
    if not pw_path.is_file():
        error(
            tr_multi(
                f"Pasvorta dosiero ne trovita aŭ ne estas regula dosiero: {pw_path}",
                f"Password file not found or is not a regular file: {pw_path}",
                f"Fichier mot de passe introuvable ou n'est pas un fichier regulier: {pw_path}",
            )
        )
        raise typer.Exit(1)

    try:
        pasvorto = pw_path.read_text(encoding="utf-8").strip()
    except OSError as e:
        error(
            tr_multi(
                f"Legado de pasvorta dosiero malsuktesis: {e}",
                f"Failed to read password file: {e}",
                f"Echec de lecture du fichier mot de passe: {e}",
            )
        )
        raise typer.Exit(1) from e

    if not pasvorto:
        error(
            tr_multi(
                "Pasvorta dosiero estas malplena.",
                "Password file is empty.",
                "Le fichier mot de passe est vide.",
            )
        )
        raise typer.Exit(1)

    dosierujo = Path(strategy["dosierujo"])
    intervalo_min = strategy["intervalo"]
    nombro = strategy["nombro"]

    if nombro < 1:
        error(
            tr_multi(
                f"Erara nombro ({nombro}) en strategio. "
                f"Rulu: sekurkopio auto --nombro 5",
                f"Invalid max copies ({nombro}) in strategy. "
                f"Run: sekurkopio auto --nombro 5",
                f"Nombre max invalide ({nombro}) dans la strategie. "
                f"Executez: sekurkopio auto --nombro 5",
            )
        )
        raise typer.Exit(1)

    if not dosierujo.exists():
        error(
            tr_multi(
                f"Backup dosierujo ne ekzistas: {dosierujo}",
                f"Backup directory does not exist: {dosierujo}",
                f"Le repertoire de sauvegarde n'existe pas: {dosierujo}",
            )
        )
        raise typer.Exit(1)

    _log_fh = None
    if log_dosiero:
        try:
            log_path = Path(log_dosiero).expanduser()
            log_path.parent.mkdir(parents=True, exist_ok=True)
            _log_fh = open(log_path, "a", encoding="utf-8")
        except OSError as e:
            error(
                tr_multi(
                    f"Ne povis malfermo log-dosiero: {e}",
                    f"Could not open log file: {e}",
                    f"Impossible d'ouvrir le fichier journal: {e}",
                )
            )
            raise typer.Exit(1) from e

    if unufoje:
        try:
            info(f"[*] {datetime.now(timezone.utc).isoformat()}")
            info(
                tr_multi(
                    "Komencante axtomatan sekurkopion...",
                    "Starting automatic backup...",
                    "Demarrage de la sauvegarde automatique...",
                )
            )
            out = _do_auto_backup(dosierujo, pasvorto, nombro)
            _service.push_history("daemon", {"dosiero": str(out)})
            info(
                tr_multi(
                    f"Sekurkopio kreita: {out.name}",
                    f"Backup created: {out.name}",
                    f"Sauvegarde creee: {out.name}",
                )
            )
        except (OSError, ValueError, ImportError) as e:
            msg = str(e)
            _log_error(_log_fh, msg)
            error(
                tr_multi(
                    f"Eraro dum sekurkopio: {e}",
                    f"Backup error: {e}",
                    f"Erreur de sauvegarde: {e}",
                )
            )
            raise typer.Exit(1) from e
        finally:
            if _log_fh:
                _log_fh.close()
        return

    info(
        tr_multi(
            f"Sekurkopio daemono startita.\n  Dosierujo : {dosierujo}\n  Intervalo : {intervalo_min} min\n  Maks. kopioj: {nombro}",
            f"Sekurkopio daemon started.\n  Directory : {dosierujo}\n  Interval : {intervalo_min} min\n  Max copies: {nombro}",
            f"Daemon sekurkopio demarre.\n  Repertoire : {dosierujo}\n  Intervalle : {intervalo_min} min\n  Max copies: {nombro}",
        )
    )

    shutdown_requested = False

    def signal_handler(signum, frame):
        nonlocal shutdown_requested
        shutdown_requested = True

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    last_backup_time = 0.0
    intervalo_sec = intervalo_min * 60

    info(
        tr_multi(
            f"Unua sekurkopio post {intervalo_min} min...",
            f"First backup in {intervalo_min} min...",
            f" premiere sauvegarde dans {intervalo_min} min...",
        )
    )

    while not shutdown_requested:
        now = time.time()
        if now - last_backup_time >= intervalo_sec:
            try:
                info(f"[*] {datetime.now(timezone.utc).isoformat()}")
                info(
                    tr_multi(
                        "Komencante axtomatan sekurkopion...",
                        "Starting automatic backup...",
                        "Demarrage de la sauvegarde automatique...",
                    )
                )
                out = _do_auto_backup(dosierujo, pasvorto, nombro)
                _service.push_history("daemon", {"dosiero": str(out)})
                info(
                    tr_multi(
                        f"Sekurkopio kreita: {out.name}",
                        f"Backup created: {out.name}",
                        f"Sauvegarde creee: {out.name}",
                    )
                )
                last_backup_time = now
            except (OSError, ValueError, ImportError) as e:
                msg = str(e)
                _log_error(_log_fh, msg)
                error(
                    tr_multi(
                        f"Eraro dum sekurkopio: {e}",
                        f"Backup error: {e}",
                        f"Erreur de sauvegarde: {e}",
                    )
                )

        for _ in range(60):
            if shutdown_requested:
                break
            time.sleep(1)

    info(
        tr_multi(
            "Daemono haltigita.",
            "Daemon stopped.",
            "Daemon arrete.",
        )
    )
