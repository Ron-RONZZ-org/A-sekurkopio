# A-sekurkopio

> **sekurkopio** (Esperanto for "backup") — A plugin for backing up and restoring A project data.

[![License: GPL v3](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org)

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Usage](#usage)
- [Commands](#commands)
- [Configuration](#configuration)
- [Development](#development)
- [License](#license)

## Overview

A-sekurkopio is a plugin for the [A project](https://github.com/Ron-RONZZ-org/A-core) that provides backup and restore functionality for all A plugins' data. It supports:

- **Encrypted backups** — Create password-protected 7z or zip archives
- **Automatic backups** — Schedule periodic backups with configurable intervals
- **Restore capability** — Restore data from backup archives
- **Multilingual UI** — Esperanto, English, and French support

## Installation

### Prerequisites

- Python 3.11 or higher
- A-core installed and configured

### Install from source

```bash
# Clone the repository
git clone https://github.com/Ron-RONZZ-org/A-sekurkopio.git
cd A-sekurkopio

# Create virtual environment
uv venv .venv

# Install dependencies
uv pip install -e ".[backup]" --python .venv/bin/python
```

### Install as A plugin

The plugin registers itself via entry points. After installation, it will be available as:

```bash
A sekurkopio --help
```

## Usage

### Quick Start

```bash
# Export all A data to encrypted archive
A sekurkopio eksporti ~/backup.7z

# Restore from backup
A sekurkopio importi ~/backup.7z

# Configure automatic backups
A sekurkopio auto ~/backups --intervalo 60 --nombro 5

# View backup history
A sekurkopio historio
```

## Commands

### `eksporti` — Export Data

Create an encrypted archive of all A data.

```bash
A sekurkopio eksporti <dosiero> [options]

# Arguments:
  dosiero              Output file path (.7z by default)

# Options:
  -p, --pasvorto TEXT     Encryption password (asked interactively if omitted)
  -f, --formato TEXT      Archive format: 7z (default) or zip
```

**Example:**

```bash
# Export with password prompt
A sekurkopio eksporti ~/backup.7z

# Export with explicit password and zip format
A sekurkopio eksporti ~/backup.zip --formato zip --pasvorto mypassword
```

### `importi` — Import Data

Restore A data from an encrypted archive.

```bash
A sekurkopio importi <dosiero> [options]

# Arguments:
  dosiero              Input archive path

# Options:
  -p, --pasvorto TEXT     Decryption password (asked interactively if omitted)
  -A, --anstatauigi       Overwrite existing files (requires typed confirmation)
```

**Example:**

```bash
# Import with password prompt
A sekurkopio importi ~/backup.7z

# Import and overwrite existing files
A sekurkopio importi ~/backup.7z --anstatauigi
```

### `auto` — Automatic Backup Configuration

Configure automatic backup strategy.

```bash
A sekurkopio auto [dosierujo] [options]

# Arguments:
  [dosierujo]          Directory to store backup files

# Options:
  -i, --intervalo INT     Backup interval in minutes (default: 60)
  -n, --nombro INT       Maximum number of backups to keep (default: 5)
```

**Example:**

```bash
# Show current configuration
A sekurkopio auto

# Configure automatic backups
A sekurkopio auto ~/backups --intervalo 30 --nombro 10
```

### `historio` — Backup History

Show the last 5 backup operations.

```bash
A sekurkopio historio
```

## Configuration

### Backup Directory

By default, backups are stored in `~/.local/share/A/sekurkopioj/`. You can customize this with the `auto` command:

```bash
A sekurkopio auto ~/my-backups
```

### Encryption

A-sekurkopio uses password-based encryption:

- **7z format** — Uses py7zr library with AES-256 encryption
- **zip format** — Standard zip encryption (less secure, more portable)

### Automatic Backups

After configuring with `auto`, you can set up automatic backups using:

1. **systemd timer** (Linux):
   ```bash
   # Create and enable systemd timer
   A sekurkopio install-systemd
   ```

2. **cron job** (all systems):
   ```bash
   # Add cron job
   A sekurkopio install-cron
   ```

3. **Manual daemon** (for testing):
   ```bash
   # Run daemon in foreground
   A sekurkopio daemon --password-file ~/password.txt
   ```

## Development

### Setup Development Environment

```bash
cd A-sekurkopio

# Create venv with dependencies
uv venv .venv && uv pip install pytest pytest-mock typer rich --python .venv/bin/python

# Install in editable mode
uv pip install -e ".[backup,dev]" --python .venv/bin/python
```

### Running Tests

```bash
PYTHONPATH=../A-core/src:src .venv/bin/python -m pytest tests/ -v
```

### Project Structure

```
A-sekurkopio/
├── src/A_sekurkopio/
│   ├── __init__.py       # Plugin exports
│   ├── cli.py            # Typer CLI commands
│   ├── service.py        # Business logic
│   └── data/
│       ├── __init__.py
│       └── storage.py    # SQLite storage
├── tests/
│   ├── test_cli.py      # CLI tests
│   └── test_service.py  # Service tests
├── pyproject.toml       # Project configuration
├── AGENTS.md            # AI agent instructions
└── README.md            # This file
```

### Code Standards

- All user-facing strings use `tr()` / `tr_multi()` for i18n
- Type hints on all public functions
- Docstrings on all public functions
- Esperanto-first with eo/en/fr support
- Import from `A` — never duplicate utilities

## License

This project is licensed under the GPL v3 License - see the [LICENSE](LICENSE) file for details.

## Related Projects

- [A-core](https://github.com/Ron-RONZZ-org/A-core) — Core framework
- [A-tempo](https://github.com/Ron-RONZZ-org/A-tempo) — Time plugin
- [A-vorto](https://github.com/Ron-RONZZ-org/A-vorto) — Wordbook plugin
- [autish](https://github.com/Ron-RONZZ-org/autish) — Legacy project (reference)

## Issues and Contributions

- Report issues: [GitHub Issues](https://github.com/Ron-RONZZ-org/A-sekurkopio/issues)
- Contributing guide: See [CONTRIBUTING.md](CONTRIBUTING.md)

---

**Note:** This plugin is part of the A project rewrite of [autish](https://github.com/Ron-RONZZ-org/autish/).
