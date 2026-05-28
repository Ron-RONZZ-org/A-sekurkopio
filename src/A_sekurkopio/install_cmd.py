"""Install systemd/cron commands for A-sekurkopio."""

from __future__ import annotations

from pathlib import Path

import typer
from A import error, info, tr_multi, confirm_action

from A_sekurkopio.service import get_service

_service = get_service()


def _resolve_pw_path(pw_path: Path) -> Path:
    """Resolve password path, auto-creating ``backup_password.txt`` in dirs.

    If *pw_path* is an existing **directory**, automatically set it to
    ``pw_path / "backup_password.txt"``.  If the resulting file does not
    exist, prompt the user to create it interactively.

    Returns the final (possibly defaulted) file path, or raises
    ``typer.Exit(0)`` if the user declines creation.
    """
    if pw_path.is_dir():
        pw_path = pw_path / "backup_password.txt"
        info(
            tr_multi(
                f"Estis dosierujo; uzas {pw_path}",
                f"Was a directory; using {pw_path}",
                f"Etait un repertoire; utilisation de {pw_path}",
            )
        )

    if pw_path.is_file():
        return pw_path

    # File does not exist — offer to create
    if not confirm_action(
        tr_multi(
            "Dosiero ne ekzistas. Cxu krei gin?",
            "File does not exist. Create it?",
            "Le fichier n'existe pas. Le creer?",
        )
    ):
        raise typer.Exit(0)

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
    return pw_path


def _prompt_pw_path() -> Path:
    """Prompt for a password file path and resolve it."""
    default_pw_file = str(Path.home() / ".config" / "A" / "backup_password.txt")
    pw_file = typer.prompt(
        tr_multi(
            "Dosiero por pasvorto",
            "Password file",
            "Fichier mot de passe",
        ),
        default=default_pw_file,
    ).strip()
    return _resolve_pw_path(Path(pw_file).expanduser())


# ── systemd ────────────────────────────────────────────────────────────────────


def _systemd_run(*args: str, check: bool = True) -> bool:
    """Run a ``systemctl --user`` command, returning success."""
    import subprocess

    try:
        subprocess.run(
            ["systemctl", "--user", *args],
            check=check,
            capture_output=True,
            timeout=10,
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


def cmd_install_systemd() -> None:
    """Install systemd timer for automatic backups.

    If a previous timer/service exists, it is stopped and disabled
    before the new files are written.
    """
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

    pw_path = _prompt_pw_path()
    intervalo_min = strategy["intervalo"]

    # ── Stop & disable old units if present ──────────────────────────
    _systemd_run("stop", "A-sekurkopio.timer", check=False)
    _systemd_run("stop", "A-sekurkopio.service", check=False)
    _systemd_run("disable", "A-sekurkopio.timer", check=False)

    # ── Write new unit files ─────────────────────────────────────────
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

    # ── Reload & start ───────────────────────────────────────────────
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


# ── cron ───────────────────────────────────────────────────────────────────────


def cmd_install_cron() -> None:
    """Add/replace cron job for automatic backups.

    If a previous ``A-sekurkopio`` cron line exists, it is removed
    and replaced with the new one.
    """
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

    pw_path = _prompt_pw_path()
    intervalo_min = strategy["intervalo"]

    import shutil
    import subprocess

    sekurkopio_bin = shutil.which("A") or "A"

    cron_expr = f"*/{intervalo_min} * * * *"
    cron_cmd = (
        f"{sekurkopio_bin} sekurkopio daemon "
        f"--pasvorto-dosiero {pw_path} --unufoje"
    )
    cron_line = f"{cron_expr} {cron_cmd} >/dev/null 2>&1\n"

    # ── Read current crontab & strip old A-sekurkopio lines ──────────
    try:
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        current_crontab = result.stdout if result.returncode == 0 else ""
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        error(
            tr_multi(
                f"Ne povis legi crontab: {e}",
                f"Could not read crontab: {e}",
                f"Impossible de lire le crontab: {e}",
            )
        )
        raise typer.Exit(1) from e

    # Filter out old lines referencing A-sekurkopio
    filtered_lines: list[str] = []
    removed_count = 0
    for line in current_crontab.splitlines(keepends=True):
        if "A-sekurkopio" in line or sekurkopio_bin in line:
            removed_count += 1
        else:
            filtered_lines.append(line)

    if removed_count:
        info(
            tr_multi(
                f"Forigis {removed_count} malnovan(j)n linio(j)n el crontab.",
                f"Removed {removed_count} old line(s) from crontab.",
                f"Supprime {removed_count} ancienne(s) ligne(s) du crontab.",
            )
        )

    # ── Preview ──────────────────────────────────────────────────────
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

    # ── Write ────────────────────────────────────────────────────────
    new_crontab = "".join(filtered_lines) + f"# A-sekurkopio\n{cron_line}"

    try:
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
