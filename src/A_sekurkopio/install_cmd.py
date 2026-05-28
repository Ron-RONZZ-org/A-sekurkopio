"""Install systemd/cron commands for A-sekurkopio."""

from __future__ import annotations

from pathlib import Path

import typer
from A import error, info, tr_multi, confirm_action

from A_sekurkopio.service import get_service

_service = get_service()


def cmd_install_systemd() -> None:
    """Install systemd timer for automatic backups."""
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
    if pw_path.is_dir():
        error(
            tr_multi(
                f"{pw_path} estas dosierujo, ne pasvorta dosiero.\n"
                f"Bonvolu specifi tekstan dosieron (ekz.: ~/.config/A/backup_password.txt)",
                f"{pw_path} is a directory, not a password file.\n"
                f"Please specify a text file (e.g.: ~/.config/A/backup_password.txt)",
                f"{pw_path} est un repertoire, pas un fichier mot de passe.\n"
                f"Veuillez specifier un fichier texte (ex.: ~/.config/A/backup_password.txt)",
            )
        )
        raise typer.Exit(1)
    if not pw_path.is_file():
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


def cmd_install_cron() -> None:
    """Add cron job for automatic backups."""
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
    if pw_path.is_dir():
        error(
            tr_multi(
                f"{pw_path} estas dosierujo, ne pasvorta dosiero.\n"
                f"Bonvolu specifi tekstan dosieron (ekz.: ~/.config/A/backup_password.txt)",
                f"{pw_path} is a directory, not a password file.\n"
                f"Please specify a text file (e.g.: ~/.config/A/backup_password.txt)",
                f"{pw_path} est un repertoire, pas un fichier mot de passe.\n"
                f"Veuillez specifier un fichier texte (ex.: ~/.config/A/backup_password.txt)",
            )
        )
        raise typer.Exit(1)
    if not pw_path.is_file():
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
    import subprocess

    sekurkopio_bin = shutil.which("A") or "A"

    # Check for existing entry BEFORE showing the preview / asking confirmation
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
                    "Sekurkopio jam estas en crontab. Neniu sango farita.",
                    "Sekurkopio is already in crontab. No changes made.",
                    "Sekurkopio est deja dans le crontab. Aucun changement.",
                )
            )
            return
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        error(
            tr_multi(
                f"Ne povis legi crontab: {e}",
                f"Could not read crontab: {e}",
                f"Impossible de lire le crontab: {e}",
            )
        )
        raise typer.Exit(1) from e

    cron_expr = f"*/{intervalo_min} * * * *"
    cron_cmd = (
        f"{sekurkopio_bin} sekurkopio daemon "
        f"--pasvorto-dosiero {pw_path} --unufoje"
    )
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

    try:
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
