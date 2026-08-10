"""
Unit-level oracle for src/services/models.py in isolation, independent of
the HTTP route layer. Observes ONLY contracts.entry_points: src.services.models
(bare) and the colon-qualified list_models / load_nemotron / unload_nemotron /
is_nemotron_loaded / load_script_model / unload_script_model /
is_script_model_loaded symbols, plus src.api.models:ModelInfo and
src.api.models:CatalogEntry for the response-schema acceptance check (AC-151).

M29 (v58) re-cut. The process-lifecycle criteria are now stated as outcomes
(AC-102..AC-106), so their tests assert reachability transitions against REAL
subprocesses rather than `send_signal` calls against mocks. A mocked process
cannot fail to die, which is exactly how the v57 oracle certified a unload path
that never killed anything (see project-trail/2026-07-25-unload-spec-lint.md).

Mock-based tests are retained only where the criterion is genuinely about a
call being made (e.g. "does not spawn a second instance"), never where it is
about a resource reaching a state.
"""
import socket
import subprocess
import sys
import time
from unittest.mock import MagicMock

import pytest

import src.services.models as models_mod
from src.api.models import CatalogEntry, ModelInfo

# A minimal OpenAI-compatible readiness server: 200 on any GET.
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

# A server that exits immediately without ever binding — models a backing
# binary that dies on startup (e.g. its port is already taken). AC-105.
_DIES_ON_START_SRC = "import sys; sys.exit(3)\n"

READY_TIMEOUT = 10.0


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _reachable(port: int) -> bool:
    """Ground truth for 'the model is running', per AC flagged assumption 3."""
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
    """Tracks every real process a test starts, and guarantees teardown."""
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

    Returns a callable: (model_id, command_src=None) -> port.

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
            # is_script_model_loaded('nemotron') routes through the module-level
            # is_nemotron_loaded(), which reads this constant rather than the
            # registry entry.
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
    """Drop every in-memory handle, keeping any spawned server running.

    This is the state any restart of the serving process produces: the handle
    map lives in module memory and does not survive, while a server spawned
    before the restart keeps running and keeps its port. Reproduced live on
    2026-07-25 under `uvicorn --reload` (a file save orphaned the backing
    server to PPID 1).
    """
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

    assert models_mod.list_models() == []


def test_list_models_returns_empty_on_non_2xx(monkeypatch):
    fake_response = MagicMock()
    fake_response.status_code = 503
    fake_response.json.return_value = {"error": "unavailable"}
    monkeypatch.setattr(models_mod.httpx, "get", MagicMock(return_value=fake_response))

    assert models_mod.list_models() == []


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


# ---------------------------------------------------------------------------
# Registry shape
# ---------------------------------------------------------------------------

def test_registry_contains_expected_script_models():
    assert set(models_mod.SCRIPT_MODELS) == {
        "nemotron",
        "deepseek-v4-flash",
        "deepseek-v4-flash-0731",
    }
    entry = models_mod.SCRIPT_MODELS["deepseek-v4-flash"]
    assert entry["chat_endpoint"].endswith("/v1/chat/completions")
    assert entry["ready_url"].endswith("/v1/models")
    assert entry["command"] == ["/Users/arc.elixir/dev/ds4/run-server.sh"]

    entry_0731 = models_mod.SCRIPT_MODELS["deepseek-v4-flash-0731"]
    assert entry_0731["id"] == "deepseek-v4-flash-0731"
    assert entry_0731["chat_endpoint"].endswith("/v1/chat/completions")
    assert entry_0731["ready_url"].endswith("/v1/models")
    assert entry_0731["command"] == ["/Users/arc.elixir/dev/ds4/run-server-0731.sh"]
    assert entry_0731["base_url"] == "http://127.0.0.1:8005"


def test_registry_0731_source_string_is_accepted_by_response_schema():
    # AC-151: the model-list response schemas accept the new source string, so
    # GET /api/v1/models and /api/v1/models/catalog can surface the 0731 model.
    info = ModelInfo(id="deepseek-v4-flash-0731", source="deepseek-v4-flash-0731")
    catalog = CatalogEntry(
        id="deepseek-v4-flash-0731", source="deepseek-v4-flash-0731", loaded=False
    )
    assert info.source == "deepseek-v4-flash-0731"
    assert catalog.source == "deepseek-v4-flash-0731"


def test_load_nemotron_expands_script_path(monkeypatch):
    monkeypatch.setattr(models_mod, "is_nemotron_loaded", lambda: False)

    fake_proc = MagicMock()
    fake_proc.poll.return_value = None
    popen_spy = MagicMock(return_value=fake_proc)
    monkeypatch.setattr(models_mod.subprocess, "Popen", popen_spy)

    # Scope the readiness mock to nemotron's OWN ready_url. A blanket 200 also
    # makes the *other* script model read as loaded, and AC-104 then correctly
    # refuses to spawn until it is evicted — which a mock can never satisfy, so
    # Popen is never called and this test's subject (expanduser on the script
    # path) is never reached. The blanket mock predates AC-104; scoping it is
    # what keeps this carried-forward test from contradicting a live AC.
    nemotron_ready = models_mod.SCRIPT_MODELS["nemotron"]["ready_url"]

    def fake_get(url, *args, **kwargs):
        if url == nemotron_ready:
            response = MagicMock()
            response.status_code = 200
            return response
        raise models_mod.httpx.ConnectError("other script model not running")

    monkeypatch.setattr(models_mod.httpx, "get", fake_get)

    models_mod.load_nemotron()

    called_args = popen_spy.call_args[0][0]
    assert not any(arg.startswith("~") for arg in called_args), (
        "NEMOTRON_SCRIPT_PATH must be expanduser-expanded before Popen"
    )


# ---------------------------------------------------------------------------
# AC-102 — unload leaves the model unreachable, handle or no handle
# ---------------------------------------------------------------------------

def test_load_then_unload_leaves_the_server_unreachable(script_model):
    """The baseline: a server this process started is actually stopped."""
    port = script_model("deepseek-v4-flash")

    assert models_mod.load_script_model("deepseek-v4-flash")["status"] == "loaded"
    assert _reachable(port)

    result = models_mod.unload_script_model("deepseek-v4-flash")

    assert result["status"] == "unloaded"
    assert _wait_until(lambda: not _reachable(port)), (
        "AC-102: after unload reported success the server was still reachable"
    )
    assert models_mod.is_script_model_loaded("deepseek-v4-flash") is False


def test_unload_stops_a_running_server_with_no_tracked_handle(script_model, spawned):
    """AC-102, the defect. Reachable but untracked — the post-restart state.

    v57 returned {"status": "unloaded"} here while the server kept running,
    kept its port, and kept being reported as loaded by the catalog.
    """
    port = script_model("deepseek-v4-flash")
    spawned(port)
    _simulate_process_restart()

    assert models_mod.is_script_model_loaded("deepseek-v4-flash") is True

    result = models_mod.unload_script_model("deepseek-v4-flash")

    assert _wait_until(lambda: not _reachable(port)), (
        "AC-102: unload must stop a running server even with no tracked handle"
    )
    assert result["status"] == "unloaded"
    assert models_mod.is_script_model_loaded("deepseek-v4-flash") is False


def test_unload_is_a_noop_when_the_model_is_not_running(script_model):
    """AC-102 second clause: already unreachable is a plain success."""
    script_model("deepseek-v4-flash")

    result = models_mod.unload_script_model("deepseek-v4-flash")

    assert result["status"] == "unloaded"
    assert models_mod.is_script_model_loaded("deepseek-v4-flash") is False


def test_unload_reports_error_when_the_model_stays_reachable(script_model, monkeypatch):
    """AC-103 (D-68 failure visibility).

    The readiness probe never goes false, so the post-condition is unreachable
    by any implementation. Reporting "unloaded" here is the defect; the
    specified outcome is a named error.
    """
    script_model("deepseek-v4-flash")

    always_ready = MagicMock()
    always_ready.status_code = 200
    monkeypatch.setattr(models_mod.httpx, "get", MagicMock(return_value=always_ready))

    result = models_mod.unload_script_model("deepseek-v4-flash")

    assert result["status"] == "error", (
        "AC-103: unload must not claim success while the model is still reachable"
    )
    assert "deepseek-v4-flash" in str(result.get("message", ""))


def test_unload_nemotron_alias_leaves_it_unreachable(script_model):
    """AC-102 via the back-compat alias."""
    port = script_model("nemotron")

    assert models_mod.load_nemotron()["status"] == "loaded"
    assert _reachable(port)

    result = models_mod.unload_nemotron()

    assert result["status"] == "unloaded"
    assert _wait_until(lambda: not _reachable(port))
    assert models_mod.is_nemotron_loaded() is False


# ---------------------------------------------------------------------------
# AC-104 — mutual exclusion is a state, not a call
# ---------------------------------------------------------------------------

def test_load_evicts_a_running_untracked_other_model(script_model, spawned):
    """AC-104, the RAM guarantee under the defect's conditions.

    v57 called unload on the other model (a no-op with no handle) and then
    spawned the requested model anyway — two RAM-heavy servers resident.
    """
    other_port = script_model("nemotron")
    requested_port = script_model("deepseek-v4-flash")

    spawned(other_port)
    _simulate_process_restart()
    assert models_mod.is_script_model_loaded("nemotron") is True

    result = models_mod.load_script_model("deepseek-v4-flash")

    assert not _reachable(other_port), (
        "AC-104: the other model must be unreachable before the second spawns"
    )
    assert result["status"] == "loaded"
    assert _reachable(requested_port)


def test_load_refuses_when_the_other_model_cannot_be_evicted(script_model, monkeypatch):
    """AC-104 second clause: an unenforceable eviction fails loudly.

    Silently proceeding is what makes the RAM guarantee a fiction.
    """
    script_model("nemotron")
    requested_port = script_model("deepseek-v4-flash")

    nemotron_ready = models_mod.SCRIPT_MODELS["nemotron"]["ready_url"]
    real_get = models_mod.httpx.get

    def fake_get(url, *args, **kwargs):
        if url == nemotron_ready:
            response = MagicMock()
            response.status_code = 200
            return response
        return real_get(url, *args, **kwargs)

    monkeypatch.setattr(models_mod.httpx, "get", fake_get)

    result = models_mod.load_script_model("deepseek-v4-flash")

    assert result["status"] == "error", (
        "AC-104: must not spawn a second model when the first cannot be evicted"
    )
    assert "nemotron" in str(result.get("message", ""))
    assert not _reachable(requested_port), (
        "AC-104: the requested model must not have been spawned"
    )


def test_load_is_idempotent_when_already_running(script_model, spawned):
    """AC-5 carried forward: no second instance for an already-ready model."""
    port = script_model("deepseek-v4-flash")
    proc = spawned(port)

    result = models_mod.load_script_model("deepseek-v4-flash")

    assert result["status"] == "loaded"
    assert proc.poll() is None, "the already-running server must be left alone"
    assert _reachable(port)


# ---------------------------------------------------------------------------
# AC-105 / AC-106 — failure paths report the right thing and leave nothing behind
# ---------------------------------------------------------------------------

def test_load_reports_child_exit_distinctly_from_the_deadline(script_model):
    """AC-105: a backing server that dies on startup is not a timeout.

    v57 reported "timeout waiting for ..." after roughly 8 s for a server that
    had already exited — for example because its port was taken by the app
    itself under the previously documented run command.
    """
    script_model("deepseek-v4-flash", command_src=_DIES_ON_START_SRC)

    started = time.monotonic()
    result = models_mod.load_script_model("deepseek-v4-flash")
    elapsed = time.monotonic() - started

    assert result["status"] == "error"
    message = str(result.get("message", "")).lower()
    assert "timeout" not in message, (
        "AC-105: a server that exited before becoming ready must not be "
        f"reported as a timeout (got {message!r})"
    )
    assert "deepseek-v4-flash" in message
    assert elapsed < 30, "must not wait out the full readiness deadline"


def test_load_deadline_leaves_the_spawned_server_unreachable(script_model, monkeypatch):
    """AC-106: the AC-6 replacement, in outcome form."""
    port = script_model("deepseek-v4-flash")
    monkeypatch.setattr(models_mod, "DEEPSEEK_READY_TIMEOUT_SECONDS", 1)

    def never_ready(*args, **kwargs):
        raise models_mod.httpx.ConnectError("not ready")

    monkeypatch.setattr(models_mod.httpx, "get", never_ready)

    result = models_mod.load_script_model("deepseek-v4-flash")

    assert result["status"] == "error"
    monkeypatch.undo()
    assert _wait_until(lambda: not _reachable(port)), (
        "AC-106: a server that missed its readiness deadline must be stopped"
    )
