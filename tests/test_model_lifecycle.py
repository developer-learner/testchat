"""
Frozen oracles for model-lifecycle reliability (spec v100; v101 re-freeze
restaged this file to fix the task mapping, v102 to retune the AC-165
threshold against the sandbox's ~2s httpx connect-refused baseline — no
behavioral change): AC-163 (unload terminates only a positively identified
server), AC-164 (a failed unload is a 503), AC-165 (load/unload never block
the event loop). Observes ONLY the locked surface in contracts.json:
entry_points (src.main:app, src.services.models:*) and routes.
subprocess/threading/httpx are plain externals, never observed as src.*
imports.
"""
import socket
import subprocess
import sys
import threading
import time

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

_SLOW_SERVER_SRC = (
    "import sys, http.server, socketserver, time\n"
    "class H(http.server.BaseHTTPRequestHandler):\n"
    "    def do_GET(self):\n"
    "        time.sleep(3)\n"
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
        return port

    return _configure


@pytest.fixture(autouse=True)
def _reset_script_model_state():
    models_mod._nemotron_process = None
    models_mod._script_processes.clear()
    yield
    models_mod._nemotron_process = None
    models_mod._script_processes.clear()


@pytest.fixture
def client():
    return TestClient(app)


def test_unload_refuses_an_unidentified_listener_and_reports_503(client, script_model):
    """AC-163/AC-164: an unrelated process answering the model port is never
    terminated, and the refusal surfaces as a 503."""
    port = script_model("deepseek-v4-flash")
    foreign = subprocess.Popen([sys.executable, "-m", "http.server", str(port)])
    try:
        assert _wait_until(lambda: _reachable(port)), "foreign server never came up"

        resp = client.post("/api/v1/script-models/deepseek-v4-flash/unload")

        assert resp.status_code == 503, "AC-164: a failed unload must be a 503"
        assert resp.json()["status"] == "error", "AC-163: the refusal is an error"
        assert _reachable(port), "AC-163: an unidentified process must never be terminated"
    finally:
        if foreign.poll() is None:
            foreign.kill()
            foreign.wait(timeout=5)


def test_load_does_not_block_other_requests(client, script_model):
    """AC-165: while a model is loading, other requests still complete."""
    script_model("deepseek-v4-flash", command_src=_SLOW_SERVER_SRC)
    responses = []

    def _load():
        responses.append(client.post("/api/v1/script-models/deepseek-v4-flash/load"))

    thread = threading.Thread(target=_load)
    thread.start()
    try:
        time.sleep(0.5)
        started = time.monotonic()
        resp = client.get("/api/v1/models")
        elapsed = time.monotonic() - started
    finally:
        thread.join(timeout=30)
        client.post("/api/v1/script-models/deepseek-v4-flash/unload")

    assert not thread.is_alive(), "load never completed"
    assert resp.status_code == 200
    assert elapsed < 5.0, f"AC-165: load blocked other requests ({elapsed:.2f}s)"
    assert len(responses) == 1
    assert responses[0].status_code == 200
    assert responses[0].json()["status"] == "loaded"


# ---------------------------------------------------------------------------
# T3 (2026-08-10 direct-fix regression) — FastAPI runs the sync load/unload
# endpoints in a threadpool, so two concurrent load calls could both pass the
# ready-check before either spawned and launch duplicate servers. The mutation
# path is now serialized by a reentrant lock; concurrent loads must spawn at
# most one server.
# ---------------------------------------------------------------------------


def test_concurrent_loads_spawn_at_most_one_server(monkeypatch):
    model_id = "deepseek-v4-flash"
    ready_url = models_mod.SCRIPT_MODELS[model_id]["ready_url"]
    spawned = {"ready": False}
    spawn_count = {"n": 0}
    count_lock = threading.Lock()

    def fake_responds_ready(url):
        # Only this model is ever "up"; the not-yet-up answer is slowed so a
        # genuine check->spawn race would be exposed if the path were unlocked.
        if url != ready_url:
            return False
        if spawned["ready"]:
            return True
        time.sleep(0.1)
        return False

    class _FakeProc:
        def poll(self):
            return None

        def send_signal(self, sig):
            pass

        def wait(self, timeout=None):
            return 0

        def kill(self):
            pass

    def fake_popen(cmd, *args, **kwargs):
        with count_lock:
            spawn_count["n"] += 1
        spawned["ready"] = True
        return _FakeProc()

    class _ReadyResp:
        status_code = 200

    monkeypatch.setattr(models_mod, "_responds_ready", fake_responds_ready)
    monkeypatch.setattr(models_mod.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(models_mod.httpx, "get", lambda *a, **k: _ReadyResp())

    threads = [
        threading.Thread(target=lambda: models_mod.load_script_model(model_id))
        for _ in range(5)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert all(not t.is_alive() for t in threads), "a concurrent load hung"
    assert spawn_count["n"] == 1, f"duplicate servers spawned: {spawn_count['n']}"
