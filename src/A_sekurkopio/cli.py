"""CLI commands for A-sekurkopio."""

from __future__ import annotations

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
    table.add_column("#", style="dim")
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


__all__ = ["app"]
