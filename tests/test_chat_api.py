"""
API-level tests for POST /api/v1/chat (M3 -- Streaming LLM Proxy).

Tests observe ONLY the locked entry point `src.main:app` and the single
locked route `POST /api/v1/chat` (INV-4). The fake upstream is a real
localhost HTTP server (pytest-httpserver) addressed via LLM_ENDPOINT.
"""
import json

from fastapi.testclient import TestClient

from src.main import app


UPSTREAM_PATH = "/v1/chat/completions"
FALLBACK_REPLY = "The language model is currently unavailable. Please try again in a moment."

client = TestClient(app)


def _sse_body(*lines):
    out = []
    for line in lines:
        payload = "[DONE]" if line == "[DONE]" else json.dumps(line)
        out.append(f"data: {payload}\n\n")
    return "".join(out).encode("utf-8")


def _delta(content):
    return {"choices": [{"delta": {"content": content}}]}


def _configure_env(monkeypatch, httpserver, timeout="5"):
    monkeypatch.setenv("LLM_ENDPOINT", httpserver.url_for(UPSTREAM_PATH))
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("LLM_SYSTEM_PROMPT", "")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", timeout)


def _parse_sse(raw_text):
    """Parse a raw SSE response body into a list of (event, data) pairs."""
    events = []
    event_name = None
    data_lines = []
    for line in raw_text.splitlines():
        if line.startswith("event:"):
            event_name = line[len("event:"):].strip()
        elif line.startswith("data:"):
            data_lines.append(line[len("data:"):].strip())
        elif line == "" and event_name is not None:
            data = json.loads("\n".join(data_lines)) if data_lines else {}
            events.append((event_name, data))
            event_name, data_lines = None, []
    return events


# ---------------------------------------------------------------------------
# AC-1: 200 + text/event-stream, opened before content is known
# ---------------------------------------------------------------------------

def test_chat_opens_event_stream_200(monkeypatch, httpserver):
    _configure_env(monkeypatch, httpserver)
    httpserver.expect_request(UPSTREAM_PATH, method="POST").respond_with_data(
        _sse_body(_delta("hi"), "[DONE]"), content_type="text/event-stream",
    )

    with client.stream("POST", "/api/v1/chat", json={"message": "hello"}) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        response.read()


# ---------------------------------------------------------------------------
# AC-5 / AC-6: token events in order, then a single terminal done
# ---------------------------------------------------------------------------

def test_chat_streams_token_events_in_order(monkeypatch, httpserver):
    _configure_env(monkeypatch, httpserver)
    httpserver.expect_request(UPSTREAM_PATH, method="POST").respond_with_data(
        _sse_body(_delta("Hel"), _delta("lo"), "[DONE]"), content_type="text/event-stream",
    )

    with client.stream("POST", "/api/v1/chat", json={"message": "hi"}) as response:
        events = _parse_sse(response.read().decode("utf-8"))

    tokens = [d["content"] for name, d in events if name == "token"]
    assert tokens == ["Hel", "lo"]


def test_chat_emits_done_after_tokens(monkeypatch, httpserver):
    _configure_env(monkeypatch, httpserver)
    httpserver.expect_request(UPSTREAM_PATH, method="POST").respond_with_data(
        _sse_body(_delta("hi"), "[DONE]"), content_type="text/event-stream",
    )

    with client.stream("POST", "/api/v1/chat", json={"message": "hi"}) as response:
        events = _parse_sse(response.read().decode("utf-8"))

    assert events[-1][0] == "done"
    assert sum(1 for name, _ in events if name == "done") == 1
    assert not any(name == "error" for name, _ in events)


# ---------------------------------------------------------------------------
# AC-9: pre-stream failure -> error only, no tokens
# ---------------------------------------------------------------------------

def test_chat_connection_error_emits_error_only(monkeypatch):
    monkeypatch.setenv("LLM_ENDPOINT", "http://127.0.0.1:1/v1/chat/completions")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("LLM_SYSTEM_PROMPT", "")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "2")

    with client.stream("POST", "/api/v1/chat", json={"message": "hi"}) as response:
        assert response.status_code == 200
        events = _parse_sse(response.read().decode("utf-8"))

    assert len(events) == 1
    name, data = events[0]
    assert name == "error"
    assert data["message"] == FALLBACK_REPLY


# ---------------------------------------------------------------------------
# AC-12: mid-stream failure -> error emitted after already-sent tokens
# ---------------------------------------------------------------------------

def test_chat_mid_stream_failure_emits_error_after_tokens(monkeypatch, httpserver):
    _configure_env(monkeypatch, httpserver)
    body = b"data: " + json.dumps(_delta("Hello")).encode("utf-8") + b"\n\n" + b"data: not-json\n\n"
    httpserver.expect_request(UPSTREAM_PATH, method="POST").respond_with_data(
        body, content_type="text/event-stream",
    )

    with client.stream("POST", "/api/v1/chat", json={"message": "hi"}) as response:
        events = _parse_sse(response.read().decode("utf-8"))

    assert events[0] == ("token", {"content": "Hello"})
    assert events[-1][0] == "error"
    assert not any(name == "done" for name, _ in events)


# ---------------------------------------------------------------------------
# AC-13: validation unchanged, no stream opened
# ---------------------------------------------------------------------------

def test_chat_missing_message_is_422_no_stream(monkeypatch, httpserver):
    _configure_env(monkeypatch, httpserver)

    response = client.post("/api/v1/chat", json={})

    assert response.status_code == 422
    assert not response.headers.get("content-type", "").startswith("text/event-stream")
