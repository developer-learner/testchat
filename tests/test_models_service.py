"""
Unit-level oracle for src/services.models.py in isolation, independent of
the HTTP route layer. Exists so src/services.models.py — a standalone
frozen file in contracts.json — has its own validated test coverage rather
than depending entirely on tests that also exercise src/api/models.py.
Observes ONLY contracts.entry_points: src.services.models (bare) and the
colon-qualified list_models / load_nemotron / unload_nemotron /
is_nemotron_loaded symbols.
"""
from unittest.mock import MagicMock

import pytest

import src.services.models as models_mod


@pytest.fixture(autouse=True)
def _reset_nemotron_state():
    models_mod._nemotron_process = None
    models_mod._script_processes.clear()
    yield
    models_mod._nemotron_process = None
    models_mod._script_processes.clear()


# ---------------------------------------------------------------------------
# list_models()
# ---------------------------------------------------------------------------

def test_list_models_includes_lmstudio_loaded_instances(monkeypatch):
    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = {
        "models": [
            {"key": "qwen/qwen3.6-27b", "loaded_instances": [{"id": "i1"}]},
            {"key": "qwen3.5-122b-a10b", "loaded_instances": []},
        ]
    }
    monkeypatch.setattr(models_mod.httpx, "get", MagicMock(return_value=fake_response))

    result = models_mod.list_models()

    ids = {(m["id"], m["source"]) for m in result}
    assert ("qwen/qwen3.6-27b", "lmstudio") in ids
    assert ("qwen3.5-122b-a10b", "lmstudio") not in ids


def test_list_models_returns_empty_on_exception(monkeypatch):
    def _raise(*args, **kwargs):
        raise models_mod.httpx.ConnectError("connection refused")

    monkeypatch.setattr(models_mod.httpx, "get", _raise)

    result = models_mod.list_models()

    assert result == []


def test_list_models_returns_empty_on_non_2xx(monkeypatch):
    fake_response = MagicMock()
    fake_response.status_code = 503
    fake_response.json.return_value = {"error": "unavailable"}
    monkeypatch.setattr(models_mod.httpx, "get", MagicMock(return_value=fake_response))

    result = models_mod.list_models()

    assert result == []


def test_list_models_omits_nemotron_when_not_loaded(monkeypatch):
    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = {"models": []}
    monkeypatch.setattr(models_mod.httpx, "get", MagicMock(return_value=fake_response))
    monkeypatch.setattr(models_mod, "is_nemotron_loaded", lambda: False)

    result = models_mod.list_models()

    assert all(m["id"] != "nemotron" for m in result)


def test_list_models_includes_nemotron_when_loaded(monkeypatch):
    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = {"models": []}
    monkeypatch.setattr(models_mod.httpx, "get", MagicMock(return_value=fake_response))
    monkeypatch.setattr(models_mod, "is_nemotron_loaded", lambda: True)

    result = models_mod.list_models()

    assert {"id": "nemotron", "source": "nemotron"} in result


# ---------------------------------------------------------------------------
# load_nemotron()
# ---------------------------------------------------------------------------

def test_load_nemotron_spawns_and_confirms_ready(monkeypatch):
    monkeypatch.setattr(models_mod, "is_nemotron_loaded", lambda: False)

    fake_proc = MagicMock()
    fake_proc.poll.return_value = None
    monkeypatch.setattr(models_mod.subprocess, "Popen", MagicMock(return_value=fake_proc))

    ready_response = MagicMock()
    ready_response.status_code = 200
    monkeypatch.setattr(models_mod.httpx, "get", MagicMock(return_value=ready_response))

    result = models_mod.load_nemotron()

    assert result["status"] == "loaded"
    assert models_mod._nemotron_process is fake_proc


def test_load_nemotron_idempotent_when_already_loaded(monkeypatch):
    monkeypatch.setattr(models_mod, "is_nemotron_loaded", lambda: True)

    spawn = MagicMock()
    monkeypatch.setattr(models_mod.subprocess, "Popen", spawn)

    result = models_mod.load_nemotron()

    assert result["status"] == "loaded"
    spawn.assert_not_called()


def test_load_nemotron_timeout_clears_process_and_errors(monkeypatch):
    monkeypatch.setattr(models_mod, "is_nemotron_loaded", lambda: False)

    fake_proc = MagicMock()
    fake_proc.poll.return_value = None
    monkeypatch.setattr(models_mod.subprocess, "Popen", MagicMock(return_value=fake_proc))
    monkeypatch.setattr(models_mod, "NEMOTRON_READY_TIMEOUT_SECONDS", 0.05)

    def _raise(*args, **kwargs):
        raise models_mod.httpx.ConnectError("not ready")

    monkeypatch.setattr(models_mod.httpx, "get", _raise)

    result = models_mod.load_nemotron()

    assert result["status"] == "error"
    fake_proc.send_signal.assert_called_once_with(models_mod.signal.SIGINT)
    assert models_mod._nemotron_process is None


def test_load_nemotron_expands_script_path(monkeypatch):
    monkeypatch.setattr(models_mod, "is_nemotron_loaded", lambda: False)

    fake_proc = MagicMock()
    fake_proc.poll.return_value = None
    popen_spy = MagicMock(return_value=fake_proc)
    monkeypatch.setattr(models_mod.subprocess, "Popen", popen_spy)

    ready_response = MagicMock()
    ready_response.status_code = 200
    monkeypatch.setattr(models_mod.httpx, "get", MagicMock(return_value=ready_response))

    models_mod.load_nemotron()

    called_args = popen_spy.call_args[0][0]
    assert not any(arg.startswith("~") for arg in called_args), (
        "NEMOTRON_SCRIPT_PATH must be expanduser-expanded before Popen"
    )


# ---------------------------------------------------------------------------
# unload_nemotron()
# ---------------------------------------------------------------------------

def test_unload_nemotron_sends_sigint(monkeypatch):
    monkeypatch.setattr(models_mod, "is_nemotron_loaded", lambda: True)

    fake_proc = MagicMock()
    fake_proc.poll.return_value = None
    fake_proc.wait.return_value = 0
    models_mod._nemotron_process = fake_proc

    result = models_mod.unload_nemotron()

    assert result["status"] == "unloaded"
    fake_proc.send_signal.assert_called_once_with(models_mod.signal.SIGINT)
    assert models_mod._nemotron_process is None


def test_unload_nemotron_idempotent_when_not_loaded(monkeypatch):
    monkeypatch.setattr(models_mod, "is_nemotron_loaded", lambda: False)

    result = models_mod.unload_nemotron()

    assert result["status"] == "unloaded"


# ---------------------------------------------------------------------------
# is_nemotron_loaded()
# ---------------------------------------------------------------------------

def test_is_nemotron_loaded_true_when_http_responds(monkeypatch):
    fake_resp = MagicMock()
    fake_resp.status_code = 200
    monkeypatch.setattr(models_mod.httpx, "get", MagicMock(return_value=fake_resp))

    assert models_mod.is_nemotron_loaded() is True


def test_is_nemotron_loaded_false_when_http_errors(monkeypatch):
    def _raise(*args, **kwargs):
        raise models_mod.httpx.ConnectError("")

    monkeypatch.setattr(models_mod.httpx, "get", _raise)

    assert models_mod.is_nemotron_loaded() is False


# ---------------------------------------------------------------------------
# Script-model registry: deepseek-v4-flash load/unload + mutual exclusion
# ---------------------------------------------------------------------------

def test_registry_contains_expected_script_models():
    assert set(models_mod.SCRIPT_MODELS) == {"nemotron", "deepseek-v4-flash"}
    entry = models_mod.SCRIPT_MODELS["deepseek-v4-flash"]
    assert entry["chat_endpoint"].endswith("/v1/chat/completions")
    assert entry["ready_url"].endswith("/v1/models")
    assert entry["command"] == ["/Users/arc.elixir/dev/ds4/run-server.sh"]


def test_load_deepseek_spawns_and_confirms_ready(monkeypatch):
    monkeypatch.setattr(
        models_mod, "is_script_model_loaded", lambda model_id: False
    )
    monkeypatch.setattr(models_mod, "is_nemotron_loaded", lambda: False)

    fake_proc = MagicMock()
    fake_proc.poll.return_value = None
    popen_spy = MagicMock(return_value=fake_proc)
    monkeypatch.setattr(models_mod.subprocess, "Popen", popen_spy)

    ready_response = MagicMock()
    ready_response.status_code = 200
    monkeypatch.setattr(models_mod.httpx, "get", MagicMock(return_value=ready_response))

    result = models_mod.load_script_model("deepseek-v4-flash")

    assert result["status"] == "loaded"
    assert popen_spy.call_args[0][0] == ["/Users/arc.elixir/dev/ds4/run-server.sh"]
    assert models_mod._script_processes["deepseek-v4-flash"] is fake_proc


def test_load_deepseek_timeout_clears_process_and_errors(monkeypatch):
    monkeypatch.setattr(
        models_mod, "is_script_model_loaded", lambda model_id: False
    )

    fake_proc = MagicMock()
    fake_proc.poll.return_value = None
    monkeypatch.setattr(models_mod.subprocess, "Popen", MagicMock(return_value=fake_proc))
    monkeypatch.setattr(models_mod, "DEEPSEEK_READY_TIMEOUT_SECONDS", 0.05)

    def _raise(*args, **kwargs):
        raise models_mod.httpx.ConnectError("not ready")

    monkeypatch.setattr(models_mod.httpx, "get", _raise)

    result = models_mod.load_script_model("deepseek-v4-flash")

    assert result["status"] == "error"
    fake_proc.send_signal.assert_called_once_with(models_mod.signal.SIGINT)
    assert models_mod._script_processes["deepseek-v4-flash"] is None


def test_unload_deepseek_sends_sigint(monkeypatch):
    monkeypatch.setattr(
        models_mod, "is_script_model_loaded", lambda model_id: True
    )

    fake_proc = MagicMock()
    fake_proc.wait.return_value = 0
    models_mod._script_processes["deepseek-v4-flash"] = fake_proc

    result = models_mod.unload_script_model("deepseek-v4-flash")

    assert result["status"] == "unloaded"
    fake_proc.send_signal.assert_called_once_with(models_mod.signal.SIGINT)
    assert models_mod._script_processes["deepseek-v4-flash"] is None


def test_load_deepseek_unloads_running_nemotron_first(monkeypatch):
    """Mutual exclusion: loading one script model evicts the other."""
    nemotron_proc = MagicMock()
    nemotron_proc.wait.return_value = 0
    models_mod._nemotron_process = nemotron_proc
    models_mod._script_processes["nemotron"] = nemotron_proc
    monkeypatch.setattr(models_mod, "is_nemotron_loaded", lambda: True)

    deepseek_loaded = {"value": False}
    real_check = models_mod.is_script_model_loaded

    def fake_loaded(model_id):
        if model_id == "deepseek-v4-flash":
            return deepseek_loaded["value"]
        return real_check(model_id)

    monkeypatch.setattr(models_mod, "is_script_model_loaded", fake_loaded)

    fake_proc = MagicMock()
    fake_proc.poll.return_value = None
    monkeypatch.setattr(models_mod.subprocess, "Popen", MagicMock(return_value=fake_proc))

    ready_response = MagicMock()
    ready_response.status_code = 200
    monkeypatch.setattr(models_mod.httpx, "get", MagicMock(return_value=ready_response))
    monkeypatch.setattr(models_mod, "DEEPSEEK_READY_TIMEOUT_SECONDS", 1)

    result = models_mod.load_script_model("deepseek-v4-flash")

    assert result["status"] == "loaded"
    nemotron_proc.send_signal.assert_called_once_with(models_mod.signal.SIGINT)
    assert models_mod._nemotron_process is None


def test_load_nemotron_unloads_running_deepseek_first(monkeypatch):
    deepseek_proc = MagicMock()
    deepseek_proc.wait.return_value = 0
    models_mod._script_processes["deepseek-v4-flash"] = deepseek_proc

    nemotron_loaded = {"value": False}

    def fake_loaded(model_id):
        if model_id == "nemotron":
            return nemotron_loaded["value"]
        return True  # deepseek reports loaded until unloaded

    monkeypatch.setattr(models_mod, "is_script_model_loaded", fake_loaded)
    monkeypatch.setattr(models_mod, "is_nemotron_loaded", lambda: False)

    fake_proc = MagicMock()
    fake_proc.poll.return_value = None
    monkeypatch.setattr(models_mod.subprocess, "Popen", MagicMock(return_value=fake_proc))

    ready_response = MagicMock()
    ready_response.status_code = 200
    monkeypatch.setattr(models_mod.httpx, "get", MagicMock(return_value=ready_response))

    result = models_mod.load_script_model("nemotron")

    assert result["status"] == "loaded"
    deepseek_proc.send_signal.assert_called_once_with(models_mod.signal.SIGINT)
    assert models_mod._script_processes["deepseek-v4-flash"] is None


def test_list_models_includes_deepseek_when_loaded(monkeypatch):
    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = {"models": []}
    monkeypatch.setattr(models_mod.httpx, "get", MagicMock(return_value=fake_response))
    monkeypatch.setattr(models_mod, "is_nemotron_loaded", lambda: False)
    monkeypatch.setattr(
        models_mod,
        "is_script_model_loaded",
        lambda model_id: model_id == "deepseek-v4-flash",
    )

    result = models_mod.list_models()

    assert {"id": "deepseek-v4-flash", "source": "deepseek-v4-flash"} in result
    assert all(m["id"] != "nemotron" for m in result)
