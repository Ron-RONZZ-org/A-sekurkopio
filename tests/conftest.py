"""Test isolation for A-sekurkopio — prevents writes to real filesystem."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolate_sekurkopio(monkeypatch, tmp_path):
    """Isolate data_dir to tmp_path and reset all singletons.

    A-sekurkopio uses module-level ``_service = get_service()`` in
    *every* command module (cli.py, auto_cmd.py, etc.).  These singletons
    are created at **import time** — before the autouse fixture runs —
    and therefore connect to the *real* database under
    ``~/.local/share/A/sekurkopio.db``.

    This fixture must reset BOTH the service singleton (in service.py)
    AND the stale references in every command module, so that tests
    always operate on a fresh connection pointing to ``tmp_path``.
    """
    import A_sekurkopio.data.storage as storage_module
    import A_sekurkopio.service as service_module

    # ── 1. Reset database singleton ──────────────────────────────────
    storage_module._db_instance = None

    # ── 2. Reset service singleton in the factory module ─────────────
    service_module._service = None

    # ── 3. Reset stale module-level ``_service`` references ─────────
    #     These were created at import time and still point to the real
    #     database.  Clearing them forces every command module to call
    #     get_service() again on first use.
    import A_sekurkopio.cli as cli_module
    import A_sekurkopio.auto_cmd as auto_cmd_module
    import A_sekurkopio.export_cmd as export_cmd_module
    import A_sekurkopio.import_cmd as import_cmd_module
    import A_sekurkopio.install_cmd as install_cmd_module

    for mod in (
        cli_module,
        auto_cmd_module,
        export_cmd_module,
        import_cmd_module,
        install_cmd_module,
    ):
        mod._service = None

    # ── 4. Redirect paths ───────────────────────────────────────────
    monkeypatch.setattr(storage_module, "data_dir", lambda: tmp_path)
    monkeypatch.setenv("A_DIR", str(tmp_path))

    # ── 5. Mock keyring (avoids system keyring calls) ────────────────
    monkeypatch.setattr("A.core.ai.save_api_key", lambda key, **kw: True)
    monkeypatch.setattr("A.core.ai.get_api_key", lambda **kw: "mock-key")
