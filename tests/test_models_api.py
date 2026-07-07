"""
Oracle for M5 AC-1 through AC-8: GET /api/v1/models and Nemotron load/unload.
Observes ONLY the locked surface in contracts.json: entry_points
(src.main:app, src.services.models:*) and routes (GET /api/v1/models,
POST /api/v1/nemotron/load, POST /api/v1/nemotron/unload). subprocess and
httpx are patched as module internals of src.services.models, not imported
as separate src.* observations.
"""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.main import app
import src.services.models as models_mod


@pytest.fixture(autouse=True)
def _reset_nemotron_state():
    models_mod._nemotron_process = None
    yield
    models_mod._nemotron_process = None


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# AC-1 / AC-2 / AC-3: GET /api/v1/models
# ---------------------------------------------------------------------------

def test_list_models_includes_lmstudio_loaded_instances(client, monkeypatch):
    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = {
        "models": [
            {"key": "qwen/qwen3.6-27b", "loaded_instances": [{"id": "i1"}]},
            {"key": "qwen3.5-122b-a10b", "loaded_instances": []},
        ]
    }
    monkeypatch.setattr(models_mod.httpx, "get", MagicMock(return_value=fake_response))

    resp = client.get("/api/v1/models")

    assert resp.status_code == 200
    ids = {(m["id"], m["source"]) for m in resp.json()["models"]}
    assert ("qwen/qwen3.6-27b", "lmstudio") in ids
    assert ("qwen3.5-122b-a10b", "lmstudio") not in ids


def test_list_models_degrades_when_lmstudio_unreachable(client, monkeypatch):
    def _raise(*args, **kwargs):
        raise models_mod.httpx.ConnectError("connection refused")

    monkeypatch.setattr(models_mod.httpx, "get", _raise)

    resp = client.get("/api/v1/models")

    assert resp.status_code == 200
    assert resp.json()["models"] == []


def test_list_models_omits_nemotron_when_not_loaded(client, monkeypatch):
    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = {"models": []}
    monkeypatch.setattr(models_mod.httpx, "get", MagicMock(return_value=fake_response))
    monkeypatch.setattr(models_mod, "is_nemotron_loaded", lambda: False)

    resp = client.get("/api/v1/models")

    ids = [m["id"] for m in resp.json()["models"]]
    assert "nemotron" not in ids


# ---------------------------------------------------------------------------
# AC-4 / AC-5 / AC-6: POST /api/v1/nemotron/load
# ---------------------------------------------------------------------------

def test_load_nemotron_spawns_and_confirms_ready(client, monkeypatch):
    monkeypatch.setattr(models_mod, "is_nemotron_loaded", lambda: False)

    fake_proc = MagicMock()
    fake_proc.poll.return_value = None
    monkeypatch.setattr(models_mod.subprocess, "Popen", MagicMock(return_value=fake_proc))

    ready_response = MagicMock()
    ready_response.status_code = 200
    monkeypatch.setattr(models_mod.httpx, "get", MagicMock(return_value=ready_response))

    resp = client.post("/api/v1/nemotron/load")

    assert resp.status_code == 200
    assert resp.json()["status"] == "loaded"
    assert models_mod._nemotron_process is fake_proc


def test_load_nemotron_idempotent_when_already_loaded(client, monkeypatch):
    monkeypatch.setattr(models_mod, "is_nemotron_loaded", lambda: True)

    spawn = MagicMock()
    monkeypatch.setattr(models_mod.subprocess, "Popen", spawn)

    resp = client.post("/api/v1/nemotron/load")

    assert resp.status_code == 200
    assert resp.json()["status"] == "loaded"
    spawn.assert_not_called()


def test_load_nemotron_timeout_returns_503_and_terminates(client, monkeypatch):
    monkeypatch.setattr(models_mod, "is_nemotron_loaded", lambda: False)

    fake_proc = MagicMock()
    fake_proc.poll.return_value = None
    monkeypatch.setattr(models_mod.subprocess, "Popen", MagicMock(return_value=fake_proc))
    monkeypatch.setattr(models_mod, "NEMOTRON_READY_TIMEOUT_SECONDS", 0.05)

    def _raise(*args, **kwargs):
        raise models_mod.httpx.ConnectError("not ready")

    monkeypatch.setattr(models_mod.httpx, "get", _raise)

    resp = client.post("/api/v1/nemotron/load")

    assert resp.status_code == 503
    assert resp.json()["status"] == "error"
    fake_proc.send_signal.assert_called_once_with(models_mod.signal.SIGINT)


# ---------------------------------------------------------------------------
# AC-7 / AC-8: POST /api/v1/nemotron/unload
# ---------------------------------------------------------------------------

def test_unload_nemotron_sends_sigint(client, monkeypatch):
    monkeypatch.setattr(models_mod, "is_nemotron_loaded", lambda: True)

    fake_proc = MagicMock()
    fake_proc.poll.return_value = None
    fake_proc.wait.return_value = 0
    models_mod._nemotron_process = fake_proc

    resp = client.post("/api/v1/nemotron/unload")

    assert resp.status_code == 200
    assert resp.json()["status"] == "unloaded"
    fake_proc.send_signal.assert_called_once_with(models_mod.signal.SIGINT)
    assert models_mod._nemotron_process is None


def test_unload_nemotron_idempotent_when_not_loaded(client, monkeypatch):
    monkeypatch.setattr(models_mod, "is_nemotron_loaded", lambda: False)

    resp = client.post("/api/v1/nemotron/unload")

    assert resp.status_code == 200
    assert resp.json()["status"] == "unloaded"
