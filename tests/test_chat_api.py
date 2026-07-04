"""HTTP-boundary tests for POST /api/v1/chat with the M2 live-LLM proxy.

Replaces the M1 echo API tests. Observes only the locked route
POST /api/v1/chat via fastapi.testclient.TestClient and the LLM_*
configuration surface, with a fake OpenAI upstream (pytest-httpserver)
addressed via LLM_ENDPOINT. Pins AC-1, AC-7, AC-11, AC-12 at the boundary.
"""
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)

FALLBACK = "The language model is currently unavailable. Please try again in a moment."
PATH = "/v1/chat/completions"


def _openai_reply(content):
    return {"choices": [{"message": {"role": "assistant", "content": content}}]}


def test_chat_returns_model_reply(monkeypatch, httpserver):
    # AC-1 / AC-12: success -> 200 {"reply": <content>}, same shape as M1.
    httpserver.expect_request(PATH, method="POST").respond_with_json(_openai_reply("live answer"))
    monkeypatch.setenv("LLM_ENDPOINT", httpserver.url_for(PATH))
    monkeypatch.setenv("LLM_MODEL", "m")
    monkeypatch.delenv("LLM_SYSTEM_PROMPT", raising=False)
    resp = client.post("/api/v1/chat", json={"message": "hello"})
    assert resp.status_code == 200
    assert resp.json() == {"reply": "live answer"}


def test_chat_upstream_failure_returns_fallback_200(monkeypatch):
    # AC-7: upstream down -> still 200 with fallback (frozen page keeps working).
    monkeypatch.setenv("LLM_ENDPOINT", "http://127.0.0.1:9/v1/chat/completions")
    monkeypatch.setenv("LLM_MODEL", "m")
    monkeypatch.delenv("LLM_SYSTEM_PROMPT", raising=False)
    resp = client.post("/api/v1/chat", json={"message": "hello"})
    assert resp.status_code == 200
    assert resp.json() == {"reply": FALLBACK}


def test_chat_missing_message_is_422(monkeypatch, httpserver):
    # AC-11: missing message field -> 422 (unchanged from M1).
    monkeypatch.setenv("LLM_ENDPOINT", httpserver.url_for(PATH))
    monkeypatch.setenv("LLM_MODEL", "m")
    resp = client.post("/api/v1/chat", json={})
    assert resp.status_code == 422


def test_chat_no_longer_echoes(monkeypatch, httpserver):
    # AC-12: reply is model content, not the M1 "Echo: " prefix.
    httpserver.expect_request(PATH, method="POST").respond_with_json(_openai_reply("real reply"))
    monkeypatch.setenv("LLM_ENDPOINT", httpserver.url_for(PATH))
    monkeypatch.setenv("LLM_MODEL", "m")
    monkeypatch.delenv("LLM_SYSTEM_PROMPT", raising=False)
    resp = client.post("/api/v1/chat", json={"message": "hello"})
    assert resp.json()["reply"] == "real reply"
    assert not resp.json()["reply"].startswith("Echo: ")
