"""UI-test fixtures (D-58): capture-shaped LLM stub + app under test.

Shapes derive from scripts/.approved/captures/ (D-56):
- lmstudio-models.json: backend reads models[].key + models[].loaded_instances
- lmstudio-chat-stream.txt: OpenAI chunk stream; thinking arrives BOTH as
  delta.reasoning_content ('think' events) and INLINE as <think>...</think>
  in delta.content ('token' events — the captured reality for the current
  LM Studio config). The stub emits both in one stream so the frozen suite
  exercises both spec paths.

Content is synthetic, shape is real (PRD A13). Everything binds loopback
only — sandbox-safe under --network none. This file must NOT import
playwright: the D-58 determinism gate scopes to playwright-importing files,
and server-readiness polling here legitimately sleeps.

M8: the app under test persists threads (TESTCHAT_DATA points at a
session temp file), and an autouse fixture clears the snapshot before each
UI test — tests must stay independent now that state survives page loads.
The fixture touches the app only for tests that actually use it.
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

STUB_PORT = 8971
APP_PORT = 8972
REPO_ROOT = Path(__file__).resolve().parent.parent

# shape: capture lmstudio-models.json (fields the backend reads). Two real
# choices so selection-stability is observable, plus a refresh-N stamp model
# whose N increments per response — the ONLY deterministic, DOM-visible
# proof that a dropdown rebuild actually happened (AC-31 would false-pass
# in the window before the rebuild otherwise).
_models_calls = 0


def _models_response() -> dict:
    global _models_calls
    _models_calls += 1
    return {
        "models": [
            {"type": "llm", "key": "alpha-model", "loaded_instances": [{"identifier": "alpha-model"}]},
            {"type": "llm", "key": "beta-model", "loaded_instances": [{"identifier": "beta-model"}]},
            {"type": "llm", "key": f"refresh-{_models_calls}", "loaded_instances": [{"identifier": "stamp"}]},
        ]
    }


# shape: capture lmstudio-chat-stream.txt (choices[0].delta chunks, [DONE])
STREAM_DELTAS = [
    {"role": "assistant", "reasoning_content": "meta thought "},
    {"content": "<think>"},
    {"content": "pondering deeply"},
    {"content": "</think>"},
    {"content": "Hello"},
    {"content": " there"},
]

_chat_requests: list[dict] = []


class _StubHandler(BaseHTTPRequestHandler):
    def log_message(self, *args) -> None:
        pass

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/api/v1/models":
            self._json(200, _models_response())
        elif self.path == "/last-chat-request":
            if _chat_requests:
                self._json(200, _chat_requests[-1])
            else:
                self._json(404, {"error": "no chat requests yet"})
        else:
            self._json(404, {"error": "unknown path"})

    def do_POST(self) -> None:
        if self.path != "/v1/chat/completions":
            self._json(404, {"error": "unknown path"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length))
        _chat_requests.append(body)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        if "SLOWPING" in (body.get("message") or ""):
            # think first, flush, hold, THEN answer — makes the pre-answer
            # "thinking..." window real and observable by Playwright auto-wait.
            for delta in [{"content": "<think>"}, {"content": "musing"}, {"content": "</think>"}]:
                chunk = {"choices": [{"index": 0, "delta": delta, "finish_reason": None}]}
                self.wfile.write(b"data: " + json.dumps(chunk).encode() + b"\n\n")
                self.wfile.flush()
            time.sleep(1.2)
            for delta in [{"content": "Hello"}, {"content": " there"}]:
                chunk = {"choices": [{"index": 0, "delta": delta, "finish_reason": None}]}
                self.wfile.write(b"data: " + json.dumps(chunk).encode() + b"\n\n")
                self.wfile.flush()
            self.wfile.write(b"data: " + json.dumps({"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}).encode() + b"\n\n")
            self.wfile.write(b"data: [DONE]\n\n")
            return
        for delta in STREAM_DELTAS:
            chunk = {"choices": [{"index": 0, "delta": delta, "finish_reason": None}]}
            self.wfile.write(b"data: " + json.dumps(chunk).encode() + b"\n\n")
        final = {"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
        self.wfile.write(b"data: " + json.dumps(final).encode() + b"\n\n")
        self.wfile.write(b"data: [DONE]\n\n")


def _wait_ready(url: str, attempts: int = 100) -> None:
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=1):
                return
        except (urllib.error.URLError, OSError):
            time.sleep(0.1)
    raise RuntimeError(f"server at {url} never became ready")


@pytest.fixture(scope="session")
def llm_stub():
    server = ThreadingHTTPServer(("127.0.0.1", STUB_PORT), _StubHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    _wait_ready(f"http://127.0.0.1:{STUB_PORT}/api/v1/models")
    yield f"http://127.0.0.1:{STUB_PORT}"
    server.shutdown()


@pytest.fixture(scope="session")
def app_url(llm_stub):
    data_path = Path(tempfile.mkdtemp(prefix="testchat-ui-")) / "threads.json"
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.main:app",
         "--host", "127.0.0.1", "--port", str(APP_PORT), "--log-level", "warning"],
        cwd=REPO_ROOT,
        env={
            **os.environ,
            "LLM_ENDPOINT": f"{llm_stub}/v1/chat/completions",
            "PYTHONPATH": str(REPO_ROOT),
            "TESTCHAT_DATA": str(data_path),
        },
    )
    try:
        _wait_ready(f"http://127.0.0.1:{APP_PORT}/")
        yield f"http://127.0.0.1:{APP_PORT}"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture(autouse=True)
def _fresh_snapshot(request):
    """Persistence isolation (M8): clear the saved snapshot before any test
    that talks to the running app. Touches nothing for pure backend tests
    (requesting app_url here would needlessly boot the app for them)."""
    if "app_url" in request.fixturenames:
        base = request.getfixturevalue("app_url")
        req = urllib.request.Request(f"{base}/api/v1/threads", method="DELETE")
        with urllib.request.urlopen(req, timeout=5):
            pass
    yield


@pytest.fixture
def last_chat_request(llm_stub):
    def fetch() -> dict:
        with urllib.request.urlopen(f"{llm_stub}/last-chat-request", timeout=5) as r:
            return json.loads(r.read())
    return fetch
