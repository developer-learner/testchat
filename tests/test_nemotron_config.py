"""M9 — Nemotron address is configurable (AC-39/AC-40).

Imports ONLY src.services.models (no src.main) so it is attributed cleanly
to the models.py task. The module reads NEMOTRON_URL at import, so the test
sets the env and reloads the module to observe the effect.
"""
import importlib


def _reload_with(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("NEMOTRON_URL", raising=False)
    else:
        monkeypatch.setenv("NEMOTRON_URL", value)
    import src.services.models as models_mod
    return importlib.reload(models_mod)


def test_default_base_is_8600(monkeypatch):
    m = _reload_with(monkeypatch, None)
    assert m.NEMOTRON_BASE_URL == "http://localhost:8600"
    assert m.NEMOTRON_CHAT_ENDPOINT == "http://localhost:8600/v1/chat/completions"
    assert m.NEMOTRON_READY_URL == "http://localhost:8600/v1/models"


def test_env_overrides_all_endpoints(monkeypatch):
    m = _reload_with(monkeypatch, "http://127.0.0.1:9100")
    assert m.NEMOTRON_BASE_URL == "http://127.0.0.1:9100"
    assert m.NEMOTRON_CHAT_ENDPOINT == "http://127.0.0.1:9100/v1/chat/completions"
    assert m.NEMOTRON_READY_URL == "http://127.0.0.1:9100/v1/models"


def test_default_is_not_the_app_port(monkeypatch):
    m = _reload_with(monkeypatch, None)
    assert ":8000" not in m.NEMOTRON_BASE_URL


def _restore(monkeypatch):
    # leave the module in its unset-default state for any later importer
    monkeypatch.delenv("NEMOTRON_URL", raising=False)
    import src.services.models as models_mod
    importlib.reload(models_mod)
