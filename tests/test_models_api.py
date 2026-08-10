"""
Oracle for the model-management routes: GET /api/v1/models and the script-model
load/unload endpoints (plus their nemotron aliases). Observes ONLY the locked
surface in contracts.json: entry_points (src.main:app, src.services.models:*)
and routes. subprocess and httpx are patched as module internals of
src.services.models, not imported as separate src.* observations.

M29 (v58) re-cut. The unload route tests now assert the OUTCOME the route
promises — that the model is no longer reachable once the response says
"unloaded" — against real subprocesses, and pin the new error contract when
that outcome cannot be reached (AC-102/AC-103). Load-failure routes gain the
distinct child-exit reporting of AC-105.
"""
import socket
import subprocess
import sys
import time
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.main import app
import src.services.models as models_mod

_SERVER_SRC = (
    "import sys, http.server, socketserver\n"
    "class H(http.server.BaseHTTPRequestHandler):\n"
    "    def do_GET(self):\n"
    "        b = b'{\"data\": []}'\n"
    "        self.send_response(200)\n"
    "        self.send_header('content-length', str(len(b)))\n"
    "        self.end_headers()\n"
    "        self.wfile.write(b)\n"
    "    def log_message(self, *a):\n"
    "        pass\n"
    "socketserver.TCPServer.allow_reuse_address = True\n"
    "socketserver.TCPServer(('127.0.0.1', int(sys.argv[1])), H).serve_forever()\n"
)

_DIES_ON_START_SRC = "import sys; sys.exit(3)\n"

READY_TIMEOUT = 10.0


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _reachable(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.25):
            return True
    except OSError:
        return False


def _wait_until(predicate, timeout: float = READY_TIMEOUT) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return predicate()


@pytest.fixture
def spawned():
    procs: list[subprocess.Popen] = []

    def _start(port: int) -> subprocess.Popen:
        proc = subprocess.Popen([sys.executable, "-c", _SERVER_SRC, str(port)])
        procs.append(proc)
        assert _wait_until(lambda: _reachable(port)), "test server never came up"
        return proc

    yield _start

    for proc in procs:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)


@pytest.fixture
def script_model(monkeypatch):
    """Repoints a registry entry at a test-local port and command.

    T1 (2026-08-10): every not-yet-configured registry entry is also repointed
    at a fixture-owned, unbound port. The load path probes the other entries'
    ready_urls while evicting, and those default to the real production ports
    (nemotron :8600, ds4 :8000, ds4-0731 :8005); a live local server must be
    invisible to the suite and never probed or killed by it. Entries configured
    by an earlier call in the same test keep their port, so the mutual-exclusion
    path still discovers the test's own spawned server (AC-104).
    """
    configured: set[str] = set()

    def _configure(model_id: str, command_src: str = _SERVER_SRC) -> int:
        port = _free_port()
        base = f"http://127.0.0.1:{port}"
        entry = dict(models_mod.SCRIPT_MODELS[model_id])
        entry["base_url"] = base
        entry["ready_url"] = base + "/v1/models"
        entry["chat_endpoint"] = base + "/v1/chat/completions"
        entry["command"] = [sys.executable, "-c", command_src, str(port)]
        monkeypatch.setitem(models_mod.SCRIPT_MODELS, model_id, entry)
        if model_id == "nemotron":
            monkeypatch.setattr(models_mod, "NEMOTRON_READY_URL", entry["ready_url"])
        configured.add(model_id)
        for other_id, other in list(models_mod.SCRIPT_MODELS.items()):
            if other_id in configured:
                continue
            other_port = _free_port()
            other_base = f"http://127.0.0.1:{other_port}"
            isolated = dict(other)
            isolated["base_url"] = other_base
            isolated["ready_url"] = other_base + "/v1/models"
            isolated["chat_endpoint"] = other_base + "/v1/chat/completions"
            isolated["command"] = [sys.executable, "-c", _SERVER_SRC, str(other_port)]
            monkeypatch.setitem(models_mod.SCRIPT_MODELS, other_id, isolated)
        return port

    return _configure


@pytest.fixture(autouse=True)
def _reset_script_model_state():
    models_mod._nemotron_process = None
    models_mod._script_processes.clear()
    yield
    # T1 teardown: unload every registry entry so a server the load route
    # spawned is terminated (identified via cmdline or sidecar; AC-163 still
    # refuses anything unidentified) instead of leaking past handle-clearing.
    for model_id in list(models_mod.SCRIPT_MODELS):
        models_mod.unload_script_model(model_id)
    models_mod._nemotron_process = None
    models_mod._script_processes.clear()


def _simulate_process_restart() -> None:
    """Drop in-memory handles while leaving spawned servers running."""
    models_mod._nemotron_process = None
    models_mod._script_processes.clear()


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

    assert "nemotron" not in [m["id"] for m in resp.json()["models"]]


# ---------------------------------------------------------------------------
# Load routes
# ---------------------------------------------------------------------------

def test_load_nemotron_spawns_and_confirms_ready(client, script_model):
    port = script_model("nemotron")

    resp = client.post("/api/v1/nemotron/load")

    assert resp.status_code == 200
    assert resp.json()["status"] == "loaded"
    assert _reachable(port)


def test_load_nemotron_idempotent_when_already_loaded(client, monkeypatch):
    monkeypatch.setattr(models_mod, "is_nemotron_loaded", lambda: True)

    spawn = MagicMock()
    monkeypatch.setattr(models_mod.subprocess, "Popen", spawn)

    resp = client.post("/api/v1/nemotron/load")

    assert resp.status_code == 200
    assert resp.json()["status"] == "loaded"
    spawn.assert_not_called()


def test_load_deepseek_via_generic_endpoint(client, script_model):
    port = script_model("deepseek-v4-flash")

    resp = client.post("/api/v1/script-models/deepseek-v4-flash/load")

    assert resp.status_code == 200
    assert resp.json()["status"] == "loaded"
    assert _reachable(port)


def test_nemotron_load_alias_matches_generic_endpoint(client, monkeypatch):
    monkeypatch.setattr(models_mod, "is_nemotron_loaded", lambda: True)

    resp = client.post("/api/v1/script-models/nemotron/load")

    assert resp.status_code == 200
    assert resp.json()["status"] == "loaded"


def test_load_unknown_script_model_is_404(client):
    assert client.post("/api/v1/script-models/not-a-model/load").status_code == 404


def test_unload_unknown_script_model_is_404(client):
    assert client.post("/api/v1/script-models/not-a-model/unload").status_code == 404


# ---------------------------------------------------------------------------
# AC-106 / AC-105: load failure paths
# ---------------------------------------------------------------------------

def test_load_deadline_returns_503_and_leaves_nothing_running(
    client, script_model, monkeypatch
):
    """AC-106 at the route: 503 AND the spawned server is actually gone."""
    port = script_model("deepseek-v4-flash")
    monkeypatch.setattr(models_mod, "DEEPSEEK_READY_TIMEOUT_SECONDS", 1)

    def never_ready(*args, **kwargs):
        raise models_mod.httpx.ConnectError("not ready")

    monkeypatch.setattr(models_mod.httpx, "get", never_ready)

    resp = client.post("/api/v1/script-models/deepseek-v4-flash/load")

    assert resp.status_code == 503
    assert resp.json()["status"] == "error"
    monkeypatch.undo()
    assert _wait_until(lambda: not _reachable(port))


def test_load_reports_child_exit_distinctly_from_deadline(client, script_model):
    """AC-105: a backing server that dies on startup is not a timeout."""
    script_model("deepseek-v4-flash", command_src=_DIES_ON_START_SRC)

    started = time.monotonic()
    resp = client.post("/api/v1/script-models/deepseek-v4-flash/load")
    elapsed = time.monotonic() - started

    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "error"
    message = str(body.get("message", "")).lower()
    assert "timeout" not in message, (
        f"AC-105: child exit must not be reported as a timeout (got {message!r})"
    )
    assert elapsed < 30


# ---------------------------------------------------------------------------
# AC-102 / AC-103: unload routes
# ---------------------------------------------------------------------------

def test_unload_route_leaves_the_server_unreachable(client, script_model):
    """AC-102 baseline through the generic endpoint."""
    port = script_model("deepseek-v4-flash")
    assert client.post("/api/v1/script-models/deepseek-v4-flash/load").status_code == 200
    assert _reachable(port)

    resp = client.post("/api/v1/script-models/deepseek-v4-flash/unload")

    assert resp.status_code == 200
    assert resp.json()["status"] == "unloaded"
    assert _wait_until(lambda: not _reachable(port)), (
        "AC-102: route reported 'unloaded' while the server was still reachable"
    )


def test_unload_route_stops_a_server_with_no_tracked_handle(
    client, script_model, spawned
):
    """AC-102, the defect, at the route boundary.

    This is what the user hits: load a model, the app restarts (a file save
    under --reload is enough), click Unload. v57 answered 200 "unloaded" and
    left the model running and still advertised as loaded by the catalog.
    """
    port = script_model("deepseek-v4-flash")
    spawned(port)
    _simulate_process_restart()

    resp = client.post("/api/v1/script-models/deepseek-v4-flash/unload")

    assert _wait_until(lambda: not _reachable(port)), (
        "AC-102: unload must stop a running server it holds no handle for"
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "unloaded"


def test_unload_route_reports_error_when_the_model_stays_reachable(
    client, script_model, monkeypatch
):
    """AC-103 (D-68): unload can fail, and the failure must be visible."""
    script_model("deepseek-v4-flash")

    always_ready = MagicMock()
    always_ready.status_code = 200
    monkeypatch.setattr(models_mod.httpx, "get", MagicMock(return_value=always_ready))

    resp = client.post("/api/v1/script-models/deepseek-v4-flash/unload")

    body = resp.json()
    assert body["status"] == "error", (
        "AC-103: must not report 'unloaded' while the model is still reachable"
    )
    assert "deepseek-v4-flash" in str(body.get("message", ""))


def test_unload_route_is_a_noop_when_not_loaded(client, script_model):
    """AC-102 second clause."""
    script_model("deepseek-v4-flash")

    resp = client.post("/api/v1/script-models/deepseek-v4-flash/unload")

    assert resp.status_code == 200
    assert resp.json()["status"] == "unloaded"


def test_unload_nemotron_alias_leaves_it_unreachable(client, script_model):
    """AC-102 through the back-compat alias."""
    port = script_model("nemotron")
    assert client.post("/api/v1/nemotron/load").status_code == 200
    assert _reachable(port)

    resp = client.post("/api/v1/nemotron/unload")

    assert resp.status_code == 200
    assert resp.json()["status"] == "unloaded"
    assert _wait_until(lambda: not _reachable(port))


def test_unload_nemotron_idempotent_when_not_loaded(client, monkeypatch):
    monkeypatch.setattr(models_mod, "is_nemotron_loaded", lambda: False)

    resp = client.post("/api/v1/nemotron/unload")

    assert resp.status_code == 200
    assert resp.json()["status"] == "unloaded"


# ---------------------------------------------------------------------------
# AC-104: mutual exclusion at the route boundary
# ---------------------------------------------------------------------------

def test_load_route_evicts_a_running_untracked_other_model(
    client, script_model, spawned
):
    """AC-104: the RAM guarantee must hold with no tracked handle.

    v57 spawned the second model while the first kept serving.
    """
    other_port = script_model("nemotron")
    requested_port = script_model("deepseek-v4-flash")

    spawned(other_port)
    _simulate_process_restart()

    resp = client.post("/api/v1/script-models/deepseek-v4-flash/load")

    assert not _reachable(other_port), (
        "AC-104: the other model must be unreachable before the second spawns"
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "loaded"
    assert _reachable(requested_port)
