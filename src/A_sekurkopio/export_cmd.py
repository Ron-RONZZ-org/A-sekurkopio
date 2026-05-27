"""Export command helpers for A-sekurkopio."""

from __future__ import annotations

from pathlib import Path

import typer
from A import error, info, tr_multi

from A_sekurkopio.service import get_service

_service = get_service()


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
        try:
            import py7zr
        except ImportError:
            raise ImportError(
                "py7zr is required for 7z backup. Install with: "
                "uv pip install A-sekurkopio[backup]"
            )

        with py7zr.SevenZipFile(str(archive_path), "w", password=password) as szf:
            for fp in files:
                szf.write(fp, fp.name)

    return len(files)


def _detect_formato(path: Path) -> str:
    """Detect archive format from file extension."""
    suffix = path.suffix.lower()
    if suffix == ".zip":
        return "zip"
    return "7z"


def cmd_eksporti(
    dosiero: str,
    pasvorto: str | None = None,
    formato: str = "7z",
) -> None:
    """Export all A data as an encrypted archive."""
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
    except (OSError, ValueError, ImportError) as e:
        error(
            tr_multi(
                f"Eksportado malsukcesis: {e}",
                f"Export failed: {e}",
                f"Echec de l'exportation: {e}",
            )
        )
        raise typer.Exit(1) from e

    _service.push_history(
        "eksporti", {"dosiero": str(out_path), "formato": formato}
    )
    info(
        tr_multi(
            f"Eksportis {count} dosiero(j)n al {out_path} (formato={formato}, cifrita).",
            f"Exported {count} file(s) to {out_path} (format={formato}, encrypted).",
            f"Exporte {count} fichier(s) vers {out_path} (format={formato}, chiffre).",
        )
    )
