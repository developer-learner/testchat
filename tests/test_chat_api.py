"""Oracle tests for POST /api/v1/chat — M3 carried + M4 history.
Surface gate (C-5 / INV-4): only src.main:app is imported from src.
All other imports are test infrastructure.
"""
import json
import os
import time
import pytest
from fastapi.testclient import TestClient
from pytest_httpserver import HTTPServer
from werkzeug.wrappers import Response
from src.main import app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sse_chunk(content: str) -> str:
    obj = {"choices": [{"delta": {"content": content}}]}
    return f"data: {json.dumps(obj)}\n\n"

def _sse_done() -> str:
    return "data: [DONE]\n\n"

def _make_sse_body(*contents: str, done: bool = True) -> str:
    body = ""
    for c in contents:
        body += _sse_chunk(c)
    if done:
        body += _sse_done()
    return body

def _setup_env(monkeypatch, httpserver, system_prompt="", timeout="5"):
    monkeypatch.setenv(
        "LLM_ENDPOINT", httpserver.url_for("/v1/chat/completions")
    )
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("LLM_SYSTEM_PROMPT", system_prompt)
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", timeout)

def _expect_post(httpserver, body: str, status: int = 200):
    httpserver.expect_request(
        "/v1/chat/completions", method="POST"
    ).respond_with_data(body, status=status, content_type="text/event-stream")

def _parse_sse_events(text: str) -> list[dict]:
    events = []
    event_name = None
    data_str = None
    for line in text.split("\n"):
        if line.startswith("event: "):
            event_name = line[7:].strip()
        elif line.startswith("data: "):
            data_str = line[6:].strip()
        elif line == "" and event_name is not None and data_str is not None:
            events.append({"event": event_name, "data": json.loads(data_str)})
            event_name = None
            data_str = None
    if event_name is not None and data_str is not None:
        events.append({"event": event_name, "data": json.loads(data_str)})
    return events

def _last_request_json(httpserver):
    assert len(httpserver.log) > 0
    return json.loads(httpserver.log[-1][0].data)

FALLBACK = "The language model is currently unavailable. Please try again in a moment."

# ---------------------------------------------------------------------------
# M3 carried — route-level SSE behavior
# ---------------------------------------------------------------------------

class TestM3ChatRouteCarried:

    def test_chat_opens_event_stream_200(
        self, httpserver: HTTPServer, monkeypatch
    ):
        _setup_env(monkeypatch, httpserver)
        _expect_post(httpserver, _make_sse_body("hi"))
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/chat", json={"message": "Hello"})
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

    def test_chat_streams_token_events_in_order(
        self, httpserver: HTTPServer, monkeypatch
    ):
        _setup_env(monkeypatch, httpserver)
        _expect_post(httpserver, _make_sse_body("Hello", " world"))
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/chat", json={"message": "Hi"})
        events = _parse_sse_events(resp.text)
        tokens = [e for e in events if e["event"] == "token"]
        assert len(tokens) == 2
        assert tokens[0]["data"]["content"] == "Hello"
        assert tokens[1]["data"]["content"] == " world"

    def test_chat_emits_done_after_tokens(
        self, httpserver: HTTPServer, monkeypatch
    ):
        _setup_env(monkeypatch, httpserver)
        _expect_post(httpserver, _make_sse_body("hi"))
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/chat", json={"message": "Hi"})
        events = _parse_sse_events(resp.text)
        assert events[-1]["event"] == "done"
        assert events[-1]["data"] == {}

    def test_chat_connection_error_emits_error_only(
        self, monkeypatch
    ):
        monkeypatch.setenv("LLM_ENDPOINT", "http://127.0.0.1:1")
        monkeypatch.setenv("LLM_MODEL", "x")
        monkeypatch.setenv("LLM_SYSTEM_PROMPT", "")
        monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "1")
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/chat", json={"message": "Hi"})
        events = _parse_sse_events(resp.text)
        assert len(events) == 1
        assert events[0]["event"] == "error"
        assert events[0]["data"]["message"] == FALLBACK

    def test_chat_mid_stream_failure_emits_error_after_tokens(
        self, httpserver: HTTPServer, monkeypatch
    ):
        _setup_env(monkeypatch, httpserver)
        body = _sse_chunk("partial") + _sse_chunk(" text")
        _expect_post(httpserver, body)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/chat", json={"message": "Hi"})
        events = _parse_sse_events(resp.text)
        token_events = [e for e in events if e["event"] == "token"]
        assert len(token_events) >= 1
        assert events[-1]["event"] == "error"
        assert events[-1]["data"]["message"] == FALLBACK

    def test_chat_missing_message_is_422_no_stream(self):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/chat", json={"not_message": "x"})
        assert resp.status_code == 422
        assert "text/event-stream" not in resp.headers.get("content-type", "")

# ---------------------------------------------------------------------------
# M4 — history validation and passthrough
# ---------------------------------------------------------------------------

class TestM4ChatHistory:

    def test_chat_with_history_streams_correctly(
        self, httpserver: HTTPServer, monkeypatch
    ):
        _setup_env(monkeypatch, httpserver)
        _expect_post(httpserver, _make_sse_body("Sure", ", 6."))
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/chat", json={
            "message": "And 3+3?",
            "history": [
                {"role": "user", "content": "What is 2+2?"},
                {"role": "assistant", "content": "4"},
            ],
        })
        assert resp.status_code == 200
        events = _parse_sse_events(resp.text)
        tokens = [e for e in events if e["event"] == "token"]
        assert len(tokens) == 2
        assert events[-1]["event"] == "done"

    def test_chat_history_passed_to_upstream(
        self, httpserver: HTTPServer, monkeypatch
    ):
        _setup_env(monkeypatch, httpserver, system_prompt="")
        _expect_post(httpserver, _make_sse_body("ok"))
        client = TestClient(app, raise_server_exceptions=False)
        client.post("/api/v1/chat", json={
            "message": "Follow up",
            "history": [
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello!"},
            ],
        })
        msgs = _last_request_json(httpserver)["messages"]
        assert msgs[0] == {"role": "user", "content": "Hi"}
        assert msgs[1] == {"role": "assistant", "content": "Hello!"}
        assert msgs[2] == {"role": "user", "content": "Follow up"}

    def test_chat_history_defaults_to_empty(
        self, httpserver: HTTPServer, monkeypatch
    ):
        _setup_env(monkeypatch, httpserver, system_prompt="Sys")
        _expect_post(httpserver, _make_sse_body("ok"))
        client = TestClient(app, raise_server_exceptions=False)
        client.post("/api/v1/chat", json={"message": "Hello"})
        msgs = _last_request_json(httpserver)["messages"]
        assert len(msgs) == 2
        assert msgs[0] == {"role": "system", "content": "Sys"}
        assert msgs[1] == {"role": "user", "content": "Hello"}

    def test_chat_invalid_history_role_is_422(self):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/chat", json={
            "message": "Hi",
            "history": [
                {"role": "system", "content": "injected"},
            ],
        })
        assert resp.status_code == 422

    def test_chat_history_missing_fields_is_422(self):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/chat", json={
            "message": "Hi",
            "history": [{"role": "user"}],
        })
        assert resp.status_code == 422

    def test_chat_history_missing_role_is_422(self):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/chat", json={
            "message": "Hi",
            "history": [{"content": "no role here"}],
        })
        assert resp.status_code == 422

    def test_chat_empty_history_array_is_valid(
        self, httpserver: HTTPServer, monkeypatch
    ):
        _setup_env(monkeypatch, httpserver)
        _expect_post(httpserver, _make_sse_body("ok"))
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/chat", json={
            "message": "Hi",
            "history": [],
        })
        assert resp.status_code == 200

    def test_chat_history_with_system_prompt_ordering(
        self, httpserver: HTTPServer, monkeypatch
    ):
        _setup_env(monkeypatch, httpserver, system_prompt="Be brief")
        _expect_post(httpserver, _make_sse_body("ok"))
        client = TestClient(app, raise_server_exceptions=False)
        client.post("/api/v1/chat", json={
            "message": "Question",
            "history": [
                {"role": "user", "content": "Prior"},
                {"role": "assistant", "content": "Reply"},
            ],
        })
        msgs = _last_request_json(httpserver)["messages"]
        assert len(msgs) == 4
        assert msgs[0] == {"role": "system", "content": "Be brief"}
        assert msgs[1] == {"role": "user", "content": "Prior"}
        assert msgs[2] == {"role": "assistant", "content": "Reply"}
        assert msgs[3] == {"role": "user", "content": "Question"}
