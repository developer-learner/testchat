"""Oracle tests for src.services.llm — M3 carried + M4 history + M5 model param + think event.
Surface gate (C-5 / INV-4): only src.services.llm:stream_reply is imported
from src.  All other imports are test infrastructure.
"""
import json
import os
import time
import pytest
from pytest_httpserver import HTTPServer
from werkzeug.wrappers import Response
from src.services.llm import stream_reply

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sse_chunk(content: str) -> str:
    obj = {"choices": [{"delta": {"content": content}}]}
    return f"data: {json.dumps(obj)}\n\n"

def _sse_reasoning_chunk(content: str) -> str:
    obj = {"choices": [{"delta": {"reasoning_content": content}}]}
    return f"data: {json.dumps(obj)}\n\n"

def _sse_chunk_empty_delta() -> str:
    obj = {"choices": [{"delta": {"role": "assistant"}}]}
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

def _collect(gen):
    return list(gen)

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

def _last_request_json(httpserver):
    assert len(httpserver.log) > 0, "httpserver received no requests"
    req = httpserver.log[-1][0]
    return json.loads(req.data)

# ---------------------------------------------------------------------------
# M3 carried — streaming behavior
# ---------------------------------------------------------------------------

class TestM3StreamReplyCarried:

    def test_request_carries_model_user_message_and_stream_true(
        self, httpserver: HTTPServer, monkeypatch
    ):
        _setup_env(monkeypatch, httpserver)
        _expect_post(httpserver, _make_sse_body("hi"))
        _collect(stream_reply("Hello"))
        body = _last_request_json(httpserver)
        assert body["model"] == "test-model"
        assert body["stream"] is True
        msgs = body["messages"]
        assert msgs[-1] == {"role": "user", "content": "Hello"}

    def test_model_parameter_overrides_env_var(
        self, httpserver: HTTPServer, monkeypatch
    ):
        _setup_env(monkeypatch, httpserver)
        _expect_post(httpserver, _make_sse_body("hi"))
        _collect(stream_reply("Hello", model="custom-model"))
        body = _last_request_json(httpserver)
        assert body["model"] == "custom-model"

    def test_system_prompt_included_when_set(
        self, httpserver: HTTPServer, monkeypatch
    ):
        _setup_env(monkeypatch, httpserver, system_prompt="Be helpful")
        _expect_post(httpserver, _make_sse_body("ok"))
        _collect(stream_reply("Hi"))
        msgs = _last_request_json(httpserver)["messages"]
        assert msgs[0] == {"role": "system", "content": "Be helpful"}
        assert msgs[-1] == {"role": "user", "content": "Hi"}

    def test_system_prompt_omitted_when_empty(
        self, httpserver: HTTPServer, monkeypatch
    ):
        _setup_env(monkeypatch, httpserver, system_prompt="")
        _expect_post(httpserver, _make_sse_body("ok"))
        _collect(stream_reply("Hi"))
        msgs = _last_request_json(httpserver)["messages"]
        assert all(m["role"] != "system" for m in msgs)

    def test_content_chunks_yielded_as_tokens_in_order(
        self, httpserver: HTTPServer, monkeypatch
    ):
        _setup_env(monkeypatch, httpserver)
        body = (
            _sse_chunk_empty_delta()
            + _sse_chunk("Hello")
            + _sse_chunk(" world")
            + _sse_done()
        )
        _expect_post(httpserver, body)
        chunks = _collect(stream_reply("Hi"))
        token_chunks = [c for c in chunks if c[0] == "token"]
        assert token_chunks == [("token", "Hello"), ("token", " world")]

    def test_clean_completion_yields_done(
        self, httpserver: HTTPServer, monkeypatch
    ):
        _setup_env(monkeypatch, httpserver)
        _expect_post(httpserver, _make_sse_body("Hi"))
        chunks = _collect(stream_reply("Hello"))
        assert chunks[-1] == ("done",)

    def test_empty_stream_yields_error_not_done(
        self, httpserver: HTTPServer, monkeypatch
    ):
        _setup_env(monkeypatch, httpserver)
        _expect_post(httpserver, _sse_done())
        chunks = _collect(stream_reply("Hello"))
        assert chunks == [("error",)]

    def test_config_read_at_call_time(
        self, httpserver: HTTPServer, monkeypatch
    ):
        _setup_env(monkeypatch, httpserver, system_prompt="First")
        _expect_post(httpserver, _make_sse_body("a"))
        _collect(stream_reply("one"))
        first_msgs = _last_request_json(httpserver)["messages"]
        assert first_msgs[0]["content"] == "First"
        httpserver.clear()
        monkeypatch.setenv("LLM_SYSTEM_PROMPT", "Second")
        _expect_post(httpserver, _make_sse_body("b"))
        _collect(stream_reply("two"))
        second_msgs = _last_request_json(httpserver)["messages"]
        assert second_msgs[0]["content"] == "Second"

    def test_connection_error_yields_error_with_no_tokens(
        self, monkeypatch
    ):
        monkeypatch.setenv("LLM_ENDPOINT", "http://127.0.0.1:1")
        monkeypatch.setenv("LLM_MODEL", "x")
        monkeypatch.setenv("LLM_SYSTEM_PROMPT", "")
        monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "1")
        chunks = _collect(stream_reply("Hi"))
        assert chunks == [("error",)]

    def test_non_2xx_yields_error_with_no_tokens(
        self, httpserver: HTTPServer, monkeypatch
    ):
        _setup_env(monkeypatch, httpserver)
        httpserver.expect_request(
            "/v1/chat/completions", method="POST"
        ).respond_with_data("err", status=500)
        chunks = _collect(stream_reply("Hi"))
        assert chunks == [("error",)]

    def test_timeout_to_first_byte_yields_error(
        self, httpserver: HTTPServer, monkeypatch
    ):
        _setup_env(monkeypatch, httpserver, timeout="1")

        def slow_handler(request):
            time.sleep(3)
            return Response(_make_sse_body("late"), content_type="text/event-stream")

        httpserver.expect_request(
            "/v1/chat/completions", method="POST"
        ).respond_with_handler(slow_handler)
        chunks = _collect(stream_reply("Hi"))
        assert chunks == [("error",)]

    def test_mid_stream_drop_yields_error_after_tokens(
        self, httpserver: HTTPServer, monkeypatch
    ):
        _setup_env(monkeypatch, httpserver)
        body = _sse_chunk("partial") + _sse_chunk(" data")
        _expect_post(httpserver, body)
        chunks = _collect(stream_reply("Hi"))
        assert ("token", "partial") in chunks
        assert ("token", " data") in chunks
        assert chunks[-1] == ("error",)

    def test_reasoning_content_yields_think_event(
        self, httpserver: HTTPServer, monkeypatch
    ):
        _setup_env(monkeypatch, httpserver)
        body = (
            _sse_reasoning_chunk("Let me")
            + _sse_reasoning_chunk(" think")
            + _sse_chunk("Hello")
            + _sse_chunk(" world")
            + _sse_done()
        )
        _expect_post(httpserver, body)
        chunks = _collect(stream_reply("Hi"))
        think_chunks = [c for c in chunks if c[0] == "think"]
        token_chunks = [c for c in chunks if c[0] == "token"]
        assert think_chunks == [("think", "Let me"), ("think", " think")]
        assert token_chunks == [("token", "Hello"), ("token", " world")]

# ---------------------------------------------------------------------------
# M4 — history in upstream messages
# ---------------------------------------------------------------------------

class TestM4HistoryUpstream:

    def test_history_entries_in_upstream_messages(
        self, httpserver: HTTPServer, monkeypatch
    ):
        _setup_env(monkeypatch, httpserver, system_prompt="")
        _expect_post(httpserver, _make_sse_body("ok"))
        history = [
            {"role": "user", "content": "What is 2+2?"},
            {"role": "assistant", "content": "4"},
        ]
        _collect(stream_reply("And 3+3?", history=history))
        msgs = _last_request_json(httpserver)["messages"]
        assert msgs[0] == {"role": "user", "content": "What is 2+2?"}
        assert msgs[1] == {"role": "assistant", "content": "4"}
        assert msgs[2] == {"role": "user", "content": "And 3+3?"}

    def test_history_with_system_prompt_ordering(
        self, httpserver: HTTPServer, monkeypatch
    ):
        _setup_env(monkeypatch, httpserver, system_prompt="Be concise")
        _expect_post(httpserver, _make_sse_body("ok"))
        history = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
        ]
        _collect(stream_reply("Follow up", history=history))
        msgs = _last_request_json(httpserver)["messages"]
        assert len(msgs) == 4
        assert msgs[0] == {"role": "system", "content": "Be concise"}
        assert msgs[1] == {"role": "user", "content": "Hi"}
        assert msgs[2] == {"role": "assistant", "content": "Hello!"}
        assert msgs[3] == {"role": "user", "content": "Follow up"}

    def test_history_without_system_prompt_ordering(
        self, httpserver: HTTPServer, monkeypatch
    ):
        _setup_env(monkeypatch, httpserver, system_prompt="")
        _expect_post(httpserver, _make_sse_body("ok"))
        history = [
            {"role": "user", "content": "First"},
            {"role": "assistant", "content": "Response"},
        ]
        _collect(stream_reply("Second", history=history))
        msgs = _last_request_json(httpserver)["messages"]
        assert len(msgs) == 3
        assert all(m["role"] != "system" for m in msgs)
        assert msgs[0] == {"role": "user", "content": "First"}
        assert msgs[1] == {"role": "assistant", "content": "Response"}
        assert msgs[2] == {"role": "user", "content": "Second"}

    def test_empty_history_matches_m3_behavior(
        self, httpserver: HTTPServer, monkeypatch
    ):
        _setup_env(monkeypatch, httpserver, system_prompt="Sys")
        _expect_post(httpserver, _make_sse_body("ok"))
        _collect(stream_reply("Hello", history=[]))
        msgs_explicit = _last_request_json(httpserver)["messages"]
        httpserver.clear()
        _expect_post(httpserver, _make_sse_body("ok"))
        _collect(stream_reply("Hello"))
        msgs_default = _last_request_json(httpserver)["messages"]
        assert msgs_explicit == msgs_default
        assert len(msgs_explicit) == 2
        assert msgs_explicit[0] == {"role": "system", "content": "Sys"}
        assert msgs_explicit[1] == {"role": "user", "content": "Hello"}

    def test_multi_turn_history_preserves_all_entries(
        self, httpserver: HTTPServer, monkeypatch
    ):
        _setup_env(monkeypatch, httpserver, system_prompt="")
        _expect_post(httpserver, _make_sse_body("ok"))
        history = [
            {"role": "user", "content": "A"},
            {"role": "assistant", "content": "B"},
            {"role": "user", "content": "C"},
            {"role": "assistant", "content": "D"},
        ]
        _collect(stream_reply("E", history=history))
        msgs = _last_request_json(httpserver)["messages"]
        assert len(msgs) == 5
        for i, h in enumerate(history):
            assert msgs[i] == h
        assert msgs[4] == {"role": "user", "content": "E"}

    def test_history_does_not_affect_streaming_behavior(
        self, httpserver: HTTPServer, monkeypatch
    ):
        _setup_env(monkeypatch, httpserver)
        _expect_post(httpserver, _make_sse_body("Hello", " world"))
        history = [{"role": "user", "content": "prior"}]
        chunks = _collect(stream_reply("now", history=history))
        assert ("token", "Hello") in chunks
        assert ("token", " world") in chunks
        assert chunks[-1] == ("done",)
