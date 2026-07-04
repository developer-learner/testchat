"""Service-level tests for src.services.llm:generate_reply (M2 LLM proxy).

Observes ONLY the locked entry point src.services.llm:generate_reply and the
LLM_* configuration surface. The upstream model is replaced by a real local
fake HTTP server (pytest-httpserver) addressed via LLM_ENDPOINT, so these tests
exercise the proxy's observable behavior without knowing how the request is
made. Pins AC-1..AC-10 at the service level.
"""
import json
import time

from src.services.llm import generate_reply

FALLBACK = "The language model is currently unavailable. Please try again in a moment."
PATH = "/v1/chat/completions"


def _openai_reply(content):
    return {"choices": [{"message": {"role": "assistant", "content": content}}]}


def _point_at(monkeypatch, httpserver):
    monkeypatch.setenv("LLM_ENDPOINT", httpserver.url_for(PATH))
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.delenv("LLM_SYSTEM_PROMPT", raising=False)


def test_success_returns_model_content(monkeypatch, httpserver):
    # AC-1
    httpserver.expect_request(PATH, method="POST").respond_with_json(_openai_reply("hi there"))
    _point_at(monkeypatch, httpserver)
    assert generate_reply("hello") == "hi there"


def test_request_carries_model_and_user_message(monkeypatch, httpserver):
    # AC-2
    httpserver.expect_request(PATH, method="POST").respond_with_json(_openai_reply("ok"))
    _point_at(monkeypatch, httpserver)
    monkeypatch.setenv("LLM_MODEL", "my-model")
    generate_reply("ping")
    body = httpserver.log[0][0].get_json()
    assert body["model"] == "my-model"
    assert any(m["role"] == "user" and m["content"] == "ping" for m in body["messages"])
    assert body["messages"][-1] == {"role": "user", "content": "ping"}


def test_system_prompt_included_when_set(monkeypatch, httpserver):
    # AC-3
    httpserver.expect_request(PATH, method="POST").respond_with_json(_openai_reply("ok"))
    _point_at(monkeypatch, httpserver)
    monkeypatch.setenv("LLM_SYSTEM_PROMPT", "You are terse.")
    generate_reply("hey")
    msgs = httpserver.log[0][0].get_json()["messages"]
    assert msgs[0] == {"role": "system", "content": "You are terse."}


def test_system_prompt_omitted_when_empty(monkeypatch, httpserver):
    # AC-4
    httpserver.expect_request(PATH, method="POST").respond_with_json(_openai_reply("ok"))
    _point_at(monkeypatch, httpserver)
    monkeypatch.setenv("LLM_SYSTEM_PROMPT", "")
    generate_reply("hey")
    msgs = httpserver.log[0][0].get_json()["messages"]
    assert all(m["role"] != "system" for m in msgs)


def test_request_is_non_streaming(monkeypatch, httpserver):
    # AC-5
    httpserver.expect_request(PATH, method="POST").respond_with_json(_openai_reply("ok"))
    _point_at(monkeypatch, httpserver)
    generate_reply("hey")
    body = httpserver.log[0][0].get_json()
    assert body.get("stream", False) is False


def test_config_read_at_call_time(monkeypatch, httpserver):
    # AC-6: endpoint resolved on each call, not at import.
    httpserver.expect_request(PATH, method="POST").respond_with_json(_openai_reply("late-bound"))
    monkeypatch.setenv("LLM_MODEL", "m")
    monkeypatch.delenv("LLM_SYSTEM_PROMPT", raising=False)
    monkeypatch.setenv("LLM_ENDPOINT", httpserver.url_for(PATH))
    assert generate_reply("hello") == "late-bound"


def test_connection_error_returns_fallback(monkeypatch):
    # AC-7: nothing listening -> fallback.
    monkeypatch.setenv("LLM_ENDPOINT", "http://127.0.0.1:9/v1/chat/completions")
    monkeypatch.setenv("LLM_MODEL", "m")
    monkeypatch.delenv("LLM_SYSTEM_PROMPT", raising=False)
    assert generate_reply("hi") == FALLBACK


def test_non_2xx_returns_fallback(monkeypatch, httpserver):
    # AC-8
    httpserver.expect_request(PATH, method="POST").respond_with_data("boom", status=500)
    _point_at(monkeypatch, httpserver)
    assert generate_reply("hi") == FALLBACK


def test_malformed_response_returns_fallback(monkeypatch, httpserver):
    # AC-9: no choices/content.
    httpserver.expect_request(PATH, method="POST").respond_with_json({"unexpected": True})
    _point_at(monkeypatch, httpserver)
    assert generate_reply("hi") == FALLBACK


def test_empty_content_returns_fallback(monkeypatch, httpserver):
    # AC-9: empty content.
    httpserver.expect_request(PATH, method="POST").respond_with_json(_openai_reply(""))
    _point_at(monkeypatch, httpserver)
    assert generate_reply("hi") == FALLBACK


def test_timeout_returns_fallback(monkeypatch, httpserver):
    # AC-10: upstream slower than LLM_TIMEOUT_SECONDS -> fallback.
    def slow(request):
        from werkzeug.wrappers import Response
        time.sleep(1.0)
        return Response(json.dumps(_openai_reply("late")), content_type="application/json")

    httpserver.expect_request(PATH, method="POST").respond_with_handler(slow)
    _point_at(monkeypatch, httpserver)
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "0.2")
    assert generate_reply("hi") == FALLBACK
