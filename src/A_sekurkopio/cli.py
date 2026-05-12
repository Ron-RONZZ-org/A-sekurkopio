from __future__ import annotations
from A import confirm_action
"""CLI commands for A-sekurkopio."""


import json
from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from A import error, info, tr, tr_multi
from A.core.paths import data_dir

from A_sekurkopio.service import get_service

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
_AUTO_INTERVAL_DEFAULT = 60
_AUTO_NOMBRO_DEFAULT = 5


@app.command("eksporti")
def eksporti(
    dosiero: str = typer.Argument(
        ...,
        help=tr_multi(
            "Eldona dosiero vojo (.7z defauxlte).",
            "Output file path (.7z by default).",
            "Chemin du fichier de sortie (.7z par defaut).",
        ),
    ),
    pasvorto: str | None = typer.Option(
        None,
        "-p",
        "--pasvorto",
        help=tr_multi(
            "Cifra pasvorto (petita interaga se omitita).",
            "Encryption password (asked interactively if omitted).",
            "Mot de passe de chiffrement (demande interactivement si omis).",
        ),
    ),
    formato: str = typer.Option(
        "7z",
        "-f",
        "--formato",
        help=tr_multi(
            "Arkiva formato. Validaj valoroj: 7z (defauxlte, pli eta), zip (pli portebla). Ekzemplo: --formato zip",
            "Archive format. Valid values: 7z (default, smaller), zip (more portable). Example: --formato zip",
            "Format d'archive. Valeurs valides: 7z (par defaut, plus petit), zip (plus portable). Exemple: --formato zip",
        ),
    ),
) -> None:
    """Eksporti cxiujn A-datumojn kiel cifrita arxivo."""
    if formato not in ("7z", "zip"):
        error(
            tr_multi(
                "Formato devas esti '7z' aux 'zip'.",
                "Format must be '7z' or 'zip'.",
                "Le format doit etre '7z' ou 'zip'.",
            )
        )
        raise typer.Exit(1)

    if not pasvorto:
        pasvorto = typer.prompt(
            tr_multi("Pasvorto", "Password", "Mot de passe"),
            hide_input=True,
            confirmation_prompt=True,
        )

    out_path = Path(dosiero)
    files = _service.collect_data_files()

    if not files:
        error(
            tr_multi(
                "Neniuj datumoj por eksporti.",
                "No data to export.",
                "Aucune donnee a exporter.",
            )
        )
        raise typer.Exit(1)

    try:
        count = _export_to_archive(out_path, pasvorto, formato, files)
    except (OSError, ValueError) as e:
        error(
            tr_multi(
                f"Eksportado malsukcesis: {e}",
                f"Export failed: {e}",
                f"Echec de l'exportation: {e}",
            )
        )
        raise typer.Exit(1) from e

    _service.push_history("eksporti", {"dosiero": str(out_path), "formato": formato})
    info(
        tr_multi(
            f"Eksportis {count} dosiero(j)n al {out_path} (formato={formato}, cifrita).",
            f"Exported {count} file(s) to {out_path} (format={formato}, encrypted).",
            f"Exporte {count} fichier(s) vers {out_path} (format={formato}, chiffre).",
        )
    )


@app.command("importi")
def importi(
    dosiero: str = typer.Argument(
        ...,
        help=tr_multi(
            "Envena arkivo vojo.",
            "Input archive path.",
            "Chemin du fichier d'archive entrant.",
        ),
    ),
    pasvorto: str | None = typer.Option(
        None,
        "-p",
        "--pasvorto",
        help=tr_multi(
            "Cifra pasvorto (petita interaga se omitita).",
            "Decryption password (asked interactively if omitted).",
            "Mot de passe de dechiffrement (demande interactivement si omis).",
        ),
    ),
    anstatauigi: bool = typer.Option(
        False,
        "-A",
        "--anstatauigi",
        help=tr_multi(
            "Anstatauxigi ekzistantajn dosierojn. Petas tajpan konfirmon.",
            "Overwrite existing files. Asks for typed confirmation.",
            "Ecraser les fichiers existants. Demande une confirmation tapee.",
        ),
    ),
) -> None:
    """Restauxri A-datumojn el cifrita arxivo."""
    in_path = Path(dosiero)
    if not in_path.exists():
        error(
            tr_multi(
                f"Dosiero ne trovita: {in_path}",
                f"File not found: {in_path}",
                f"Fichier non trouve: {in_path}",
            )
        )
        raise typer.Exit(1)

    formato = _detect_formato(in_path)

    if not pasvorto:
        pasvorto = typer.prompt(
            tr_multi("Pasvorto", "Password", "Mot de passe"),
            hide_input=True,
        )

    if anstatauigi:
        typed = typer.prompt(
            tr_multi(
                "Por konfirmi anstatauxigon, tajpu: anstatauigi",
                "To confirm overwrite, type: anstatauigi",
                "Pour confirmer l'ecrasement, tapez: anstatauigi",
            )
        ).strip()
        if typed not in ("anstatauigi", "anstataŭigi"):
            error(
                tr_multi(
                    "Konfirmo malsukcesis. Operacio nuligita.",
                    "Confirmation failed. Operation cancelled.",
                    "Echec de la confirmation. Operation annulee.",
                )
            )
            raise typer.Exit(1)

    try:
        count = _import_from_archive(in_path, pasvorto, formato, overwrite=anstatauigi)
    except (OSError, ValueError) as e:
        error(
            tr_multi(
                f"Importado malsukcesis: {e}",
                f"Import failed: {e}",
                f"Echec de l'importation: {e}",
            )
        )
        raise typer.Exit(1) from e

    _service.push_history(
        "importi", {"dosiero": str(in_path), "anstatauigi": anstatauigi}
    )
    info(
        tr_multi(
            f"Importis {count} dosiero(j)n el {in_path}.",
            f"Imported {count} file(s) from {in_path}.",
            f"Importe {count} fichier(s) depuis {in_path}.",
        )
    )


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


@app.command("auto")
def auto(
    dosierujo: str | None = typer.Argument(
        None,
        help=tr_multi(
            "Dosierujo por konservi sekurkopiojn.",
            "Directory to store backup files.",
            "Repertoire pour stocker les sauvegardes.",
        ),
    ),
    intervalo: int | None = typer.Option(
        None,
        "-i",
        "--intervalo",
        help=tr_multi(
            f"Sekurkopia intertempo en minutoj (defauxlte {_AUTO_INTERVAL_DEFAULT}).",
            f"Backup interval in minutes (default {_AUTO_INTERVAL_DEFAULT}).",
            f"Intervalle de sauvegarde en minutes (defaut {_AUTO_INTERVAL_DEFAULT}).",
        ),
    ),
    nombro: int | None = typer.Option(
        None,
        "-n",
        "--nombro",
        help=tr_multi(
            f"Maksimuma nombro da sekurkopioj konservi (defauxlte {_AUTO_NOMBRO_DEFAULT}).",
            f"Maximum number of backups to keep (default {_AUTO_NOMBRO_DEFAULT}).",
            f"Nombre maximum de sauvegardes a conserver (defaut {_AUTO_NOMBRO_DEFAULT}).",
        ),
    ),
) -> None:
    """Mastrumi auxtomatajn periodajn sekurkopiojn."""
    strategy = _service.load_auto_strategy()

    if dosierujo is None and intervalo is None and nombro is None:
        if not strategy:
            info(
                tr_multi(
                    "Neniu auxtomata sekurkopio konfigurita.",
                    "No automatic backup configured.",
                    "Aucune sauvegarde automatique configuree.",
                )
            )
            return
        else:
            table = Table(
                title=tr_multi(
                    "Auxtomata sekurkopio-strategio",
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
            f"Auxtomata sekurkopio agordita:\n  Dosierujo : {new_dir}\n  Intervalo : {new_intervalo} min\n  Maks. kopioj: {new_nombro}",
            f"Automatic backup configured:\n  Directory : {new_dir}\n  Interval : {new_intervalo} min\n  Max copies: {new_nombro}",
            f"Sauvegarde automatique configuree:\n  Repertoire : {new_dir}\n  Intervalle : {new_intervalo} min\n  Max copies: {new_nombro}",
        )
    )


def _export_to_archive(
    archive_path: Path,
    password: str,
    formato: str = "7z",
    files: list[Path] | None = None,
) -> int:
    """Create an encrypted archive. Returns file count."""
    if files is None:
        files = _service.collect_data_files()

    if not files:
        return 0

    if formato == "zip":
        import io
        import zipfile

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for fp in files:
                zf.write(fp, fp.name)
        archive_path.write_bytes(buf.getvalue())
    else:
        import py7zr

        with py7zr.SevenZipFile(str(archive_path), "w", password=password) as szf:
            for fp in files:
                szf.write(fp, fp.name)

    return len(files)


def _import_from_archive(
    archive_path: Path,
    password: str,
    formato: str,
    overwrite: bool = False,
) -> int:
    """Restore data files from an encrypted archive. Returns file count."""
    if formato == "zip":
        import io
        import zipfile

        raw = archive_path.read_bytes()
        buf = io.BytesIO(raw)
        with zipfile.ZipFile(buf, "r") as zf:
            count = 0
            for member in zf.namelist():
                dest = data_dir() / member
                if dest.exists() and not overwrite:
                    continue
                data_dir().mkdir(parents=True, exist_ok=True)
                dest.write_bytes(zf.read(member))
                count += 1
            return count
    else:
        import py7zr

        with py7zr.SevenZipFile(
            str(archive_path), "r", password=password
        ) as szf:
            szf.extractall(path=str(data_dir()))

        # Count extracted files
        count = len(list(data_dir().glob("*.db")))
        return count


def _detect_formato(path: Path) -> str:
    """Detect archive format from file extension."""
    suffix = path.suffix.lower()
    if suffix == ".zip":
        return "zip"
    return "7z"


@app.command("daemon")
def daemon(
    pasvorto_dosiero: str | None = typer.Option(
        None,
        "-p",
        "--pasvorto-dosiero",
        help=tr_multi(
            "Vojo al dosiero enhavanta la pasvorton (unu linio).",
            "Path to file containing password (one line).",
            "Chemin du fichier contenant le mot de passe (une ligne).",
        ),
    ),
    unufoje: bool = typer.Option(
        False,
        "--unufoje",
        help=tr_multi(
            "Fari unu sekurkopio kaj eliri (por systemd/cron).",
            "Run one backup and exit (for systemd/cron).",
            "Effectuer une sauvegarde et quitter (pour systemd/cron).",
        ),
    ),
) -> None:
    """Ruli axtomatan sekurkopion daemono."""
    import signal
    import time

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
    if not pw_path.exists():
        error(
            tr_multi(
                f"Pasvorta dosiero ne trovita: {pw_path}",
                f"Password file not found: {pw_path}",
                f"Fichier mot de passe non trouve: {pw_path}",
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
        except (OSError, ValueError) as e:
            error(
                tr_multi(
                    f"Eraro dum sekurkopio: {e}",
                    f"Backup error: {e}",
                    f"Erreur de sauvegarde: {e}",
                )
            )
            raise typer.Exit(1) from e
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
            except (OSError, ValueError) as e:
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


@app.command("install-systemd")
def install_systemd() -> None:
    """Instali systemd timer por axtomataj sekurkopioj."""
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

    intervalo_min = strategy["intervalo"]

    default_pw_file = str(Path.home() / ".config" / "A" / "backup_password.txt")
    pw_file = typer.prompt(
        tr_multi(
            "Dosiero por pasvorto",
            "Password file",
            "Fichier mot de passe",
        ),
        default=default_pw_file,
    ).strip()

    pw_path = Path(pw_file).expanduser()
    if not pw_path.exists():
        if confirm_action(
            tr_multi(
                "Dosiero ne ekzistas. Cxu krei gin?",
                "File does not exist. Create it?",
                "Le fichier n'existe pas. Le creer?",
            )
        ):
            pasvorto = typer.prompt(
                tr_multi("Pasvorto", "Password", "Mot de passe"),
                hide_input=True,
                confirmation_prompt=True,
            )
            pw_path.parent.mkdir(parents=True, exist_ok=True)
            pw_path.write_text(pasvorto, encoding="utf-8")
            pw_path.chmod(0o600)
            info(
                tr_multi(
                    f"Pasvorto konservita al: {pw_path}",
                    f"Password saved to: {pw_path}",
                    f"Mot de passe enregistre: {pw_path}",
                )
            )
        else:
            raise typer.Exit(0)

    systemd_dir = Path.home() / ".config" / "systemd" / "user"
    systemd_dir.mkdir(parents=True, exist_ok=True)

    service_file = systemd_dir / "A-sekurkopio.service"
    timer_file = systemd_dir / "A-sekurkopio.timer"

    service_content = """[Unit]
Description=A automatic backup service
After=network.target

[Service]
Type=oneshot
ExecStart=A sekurkopio daemon --pasvorto-dosiero {pw_file} --unufoje
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
""".format(pw_file=pw_path)

    timer_content = f"""[Unit]
Description=A automatic backup timer
Requires=A-sekurkopio.service

[Timer]
OnBootSec=5min
OnUnitInactiveSec={intervalo_min}min
Persistent=true

[Install]
WantedBy=timers.target
"""

    service_file.write_text(service_content, encoding="utf-8")
    timer_file.write_text(timer_content, encoding="utf-8")

    info(
        tr_multi(
            f"Systemd dosieroj kreitaj:\n  {service_file}\n  {timer_file}",
            f"Systemd files created:\n  {service_file}\n  {timer_file}",
            f"Fichiers systemd creats:\n  {service_file}\n  {timer_file}",
        )
    )

    import subprocess

    try:
        subprocess.run(
            ["systemctl", "--user", "daemon-reload"],
            check=True,
            capture_output=True,
            timeout=10,
        )
        subprocess.run(
            ["systemctl", "--user", "enable", "A-sekurkopio.timer"],
            check=True,
            capture_output=True,
            timeout=10,
        )
        subprocess.run(
            ["systemctl", "--user", "start", "A-sekurkopio.timer"],
            check=True,
            capture_output=True,
            timeout=10,
        )
        info(
            tr_multi(
                "Systemd timer ebligita kaj startita.",
                "Systemd timer enabled and started.",
                "Timer systemd active et demarre.",
            )
        )
        info(
            tr_multi(
                "Por vidi staton:\n  systemctl --user status A-sekurkopio.timer",
                "To view status:\n  systemctl --user status A-sekurkopio.timer",
                "Pour voir le statut:\n  systemctl --user status A-sekurkopio.timer",
            )
        )
    except subprocess.CalledProcessError as e:
        error(
            tr_multi(
                f"Averto: Ne povis axtomate ebligi/starti la timer: {e}",
                f"Warning: Could not enable/start timer automatically: {e}",
                f"Attention: Impossible d'activer/demarrer le timer: {e}",
            )
        )
    except subprocess.TimeoutExpired:
        error(
            tr_multi(
                "Averto: Systemd komando ekster tempo.",
                "Warning: systemd command timed out.",
                "Attention: commande systemd expiree.",
            )
        )


@app.command("install-cron")
def install_cron() -> None:
    """Aldoni cron laboron por axtomataj sekurkopioj."""
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

    intervalo_min = strategy["intervalo"]

    default_pw_file = str(Path.home() / ".config" / "A" / "backup_password.txt")
    pw_file = typer.prompt(
        tr_multi(
            "Dosiero por pasvorto",
            "Password file",
            "Fichier mot de passe",
        ),
        default=default_pw_file,
    ).strip()

    pw_path = Path(pw_file).expanduser()
    if not pw_path.exists():
        if confirm_action(
            tr_multi(
                "Dosiero ne ekzistas. Cxu krei gin?",
                "File does not exist. Create it?",
                "Le fichier n'existe pas. Le creer?",
            )
        ):
            pasvorto = typer.prompt(
                tr_multi("Pasvorto", "Password", "Mot de passe"),
                hide_input=True,
                confirmation_prompt=True,
            )
            pw_path.parent.mkdir(parents=True, exist_ok=True)
            pw_path.write_text(pasvorto, encoding="utf-8")
            pw_path.chmod(0o600)
            info(
                tr_multi(
                    f"Pasvorto konservita al: {pw_path}",
                    f"Password saved to: {pw_path}",
                    f"Mot de passe enregistre: {pw_path}",
                )
            )
        else:
            raise typer.Exit(0)

    import shutil

    sekurkopio_bin = shutil.which("A") or "A"

    cron_expr = f"*/{intervalo_min} * * * *"
    cron_cmd = f"{sekurkopio_bin} sekurkopio daemon --pasvorto-dosiero {pw_path} --unufoje"
    cron_line = f"{cron_expr} {cron_cmd} >/dev/null 2>&1\n"

    info(
        tr_multi(
            f"Aldononta cron linion:\n{cron_line}",
            f"Adding cron line:\n{cron_line}",
            f"Ajout de la ligne cron:\n{cron_line}",
        )
    )

    if not confirm_action(
        tr_multi(
            "Cxu aldoni cxi tion al via crontab?",
            "Add this to your crontab?",
            "Ajouter ceci a votre crontab?",
        )
    ):
        raise typer.Exit(0)

    import subprocess

    try:
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        current_crontab = result.stdout if result.returncode == 0 else ""

        if "A-sekurkopio" in current_crontab or sekurkopio_bin in current_crontab:
            info(
                tr_multi(
                    "Sekurkopio jam estas en crontab.",
                    "Sekurkopio is already in crontab.",
                    "Sekurkopio est deja dans le crontab.",
                )
            )
            return

        new_crontab = current_crontab + f"# A-sekurkopio\n{cron_line}"

        subprocess.run(
            ["crontab", "-"],
            input=new_crontab,
            text=True,
            check=True,
            timeout=5,
        )
        info(
            tr_multi(
                "Cron laboro aldonita.",
                "Cron job added.",
                "Tache cron ajoutee.",
            )
        )
        info(
            tr_multi(
                "Por vidi vian crontab:\n  crontab -l",
                "To view your crontab:\n  crontab -l",
                "Pour voir votre crontab:\n  crontab -l",
            )
        )
    except subprocess.CalledProcessError as e:
        error(
            tr_multi(
                f"Eraro: {e}",
                f"Error: {e}",
                f"Erreur: {e}",
            )
        )
    except subprocess.TimeoutExpired:
        error(
            tr_multi(
                "Eraro: crontab komando ekster tempo.",
                "Error: crontab command timed out.",
                "Erreur: commande crontab expiree.",
            )
        )


def _do_auto_backup(dosierujo: Path, pasvorto: str, nombro: int) -> Path:
    """Create one auto-backup file. Returns the path created."""
    import py7zr

    dosierujo.mkdir(parents=True, exist_ok=True)

    # Rotate old backups
    files = sorted(
        dosierujo.glob("A_backup_*.7z"),
        key=lambda p: p.stat().st_mtime,
    )
    while len(files) >= nombro:
        files[0].unlink(missing_ok=True)
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


__all__ = ["app"]
