"""Test isolation for A-sekurkopio — prevents writes to real filesystem."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolate_sekurkopio(monkeypatch, tmp_path):
    """Isolate data_dir to tmp_path and mock keyring access."""
    import A_sekurkopio.data.storage as storage_module

    # Reset singleton to force fresh connection on each test
    storage_module._db_instance = None

    monkeypatch.setattr(storage_module, "data_dir", lambda: tmp_path)
    monkeypatch.setattr("A.core.ai.save_api_key", lambda key, **kw: True)
    monkeypatch.setattr("A.core.ai.get_api_key", lambda **kw: "mock-key")
    monkeypatch.setenv("A_DIR", str(tmp_path))
