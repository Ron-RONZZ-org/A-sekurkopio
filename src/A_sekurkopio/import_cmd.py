"""Import command helpers for A-sekurkopio."""

from __future__ import annotations

from pathlib import Path

import typer
from A import error, info, tr_multi
from A.core.paths import data_dir

from A_sekurkopio.export_cmd import _detect_formato
from A_sekurkopio.service import get_service

_service = get_service()


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
        try:
            import py7zr
        except ImportError:
            raise ImportError(
                "py7zr is required for 7z backup. Install with: "
                "uv pip install A-sekurkopio[backup]"
            )

        with py7zr.SevenZipFile(
            str(archive_path), "r", password=password
        ) as szf:
            szf.extractall(path=str(data_dir()))

        count = len(list(data_dir().glob("*.db")))
        return count


def cmd_importi(
    dosiero: str,
    pasvorto: str | None = None,
    anstatauigi: bool = False,
) -> None:
    """Restore A data from an encrypted archive."""
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
    except (OSError, ValueError, ImportError) as e:
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
