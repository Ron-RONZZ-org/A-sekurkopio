# AGENTS.md — Rules for A-sekurkopio

This file extends root A-core AGENTS.md for the A-sekurkopio plugin.

## Project Overview

A-sekurkopio is a plugin for backing up and restoring A project data. It provides encrypted archive creation, automatic backup scheduling, and restore capabilities.

## Relationship to A-core

**A-sekurkopio depends on A-core** for:
- `A` package for i18n (`tr()`, `tr_multi()`), output (`error()`, `info()`)
- Plugin discovery via entry points
- SQLite utilities (`A.data.base.SQLiteDB`)
- Path management (`A.core.paths.data_dir()`)
- **API Reference**: See [A-core AGENTS.md](https://github.com/Ron-RONZZ-org/A-core/blob/main/AGENTS.md#api-reference)

All source code must import from `A`, not duplicate utilities.

## Architecture

```
src/A_sekurkopio/
├── __init__.py        # Plugin exports (app)
├── cli.py             # Typer app (~85 lines) — app setup, historio, registrations
├── export_cmd.py      # eksporti command + archive helpers (~118 lines)
├── import_cmd.py      # importi command + archive restore helpers (~122 lines)
├── auto_cmd.py        # auto + daemon commands + helpers (~340 lines)
├── install_cmd.py     # install-systemd + install-cron commands (~304 lines)
├── service.py         # Business logic (backup/restore operations)
└── data/
    ├── __init__.py    # Data layer exports
    └── storage.py     # SQLite (uses A.data.base) — get_db() singleton
```

**Rule:** Service layer uses A-core, CLI layer uses Typer + A output utils.

## Code Standards

1. Import from `A` — never duplicate utilities
2. Use `tr()` / `tr_multi()` for all user-facing strings
3. Use `error()` for errors, `info()` for info
4. Type hints on all public functions
5. Docstrings on all public functions
6. Tests required (pytest-mock for CLI tests)
7. Use WAL mode for SQLite (handled by A.data.base)
8. Esperanto-first UI with multilingual support (eo/en/fr)

## CLI Commands

| Command | Description |
|---------|-------------|
| `sekurkopio eksporti <dosiero>` | Export data to encrypted archive |
| `sekurkopio importi <dosiero>` | Restore data from encrypted archive |
| `sekurkopio auto [dosierujo]` | Configure automatic backups |
| `sekurkopio historio` | Show backup history |
| `sekurkopio daemon` | Run automatic backup daemon |
| `sekurkopio install-systemd` | Set up systemd timer |
| `sekurkopio install-cron` | Set up cron job |

## Features

1. **Encrypted backups** — 7z (default) and zip formats
2. **Automatic backups** — Configurable interval and rotation
3. **History tracking** — Last 5 operations stored in SQLite
4. **Multilingual UI** — Esperanto, English, French

## Testing

```bash
cd A-sekurkopio
uv venv .venv && uv pip install pytest pytest-mock typer rich --python .venv/bin/python
PYTHONPATH=../A-core/src:src .venv/bin/python -m pytest tests/
```

### Test Coverage

| Module | Tests | Description |
|--------|-------|-------------|
| `test_cli.py` | 8 | CLI commands via CliRunner |
| `test_service.py` | 6 | Service layer operations |
| `test_storage.py` | 3 | Storage layer (singleton, schema, WAL mode) |

**Total: 17 tests — all passing**



## Package Manager: `uv` is Required

All A-ecosystem development **must** use `uv` as the package manager:

| Operation | Command |
|-----------|---------|
| Install dependencies | `uv pip install <pkg>` |
| Install project in dev mode | `uv pip install -e .` |
| Run tests | `uv run pytest tests/` |
| Install CLI tools (poetry, etc.) | `uv tool install <tool>` |
| Add dev dependency | `uv add --dev <pkg>` |

**Exceptions:**
- `pip` in README install instructions is acceptable for end users who may not have `uv`
- Readthedocs platform build may require `pip` (platform constraint)
- Runtime `install-on-confirmation` code may fall back to `pip` if `uv` is unavailable (see A-core AGENTS.md)

## What to Avoid

- Don't duplicate A-core utilities
- Don't skip i18n (use `tr()` / `tr_multi()`)
- Don't use `print()` — use `A` output functions
- Don't hardcode paths — use `A.core.paths.data_dir()`
- Don't use `click` directly — use Typer

## Dependencies

| Dependency | Purpose |
|-----------|---------|
| `py7zr>=0.20` | 7z archive creation (optional) |
| `typer>=0.12` | CLI framework |
| `rich>=13.0` | Rich terminal output |

## Reference

Based on [autish sekurkopio](https://github.com/Ron-RONZZ-org/autish/blob/master/autish/commands/sekurkopio.py) — the original implementation in the legacy autish project.

## Branch Convention

All A-* repos use `main` as the primary branch. Use `main` for all development.
