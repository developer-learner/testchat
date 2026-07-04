"""
Unit tests for src.services.llm:stream_reply (M3 -- Streaming LLM Proxy).

Tests observe ONLY the locked entry point `src.services.llm:stream_reply`
and the `LLM_*` environment surface (INV-4). The fake upstream is a real
localhost HTTP server (pytest-httpserver) addressed via LLM_ENDPOINT; no
test inspects how the request is made.

Chunk contract under test (see ERD -> Data models -> StreamChunk):
    ("token", content: str)  -- one non-empty content increment
    ("done",)                -- clean end of stream, only after >=1 token
    ("error",)               -- any failure: pre-stream, mid-stream, or a
                                 clean-but-empty completion (AC-7)
"""
import json
import time

from werkzeug.wrappers import Response

from src.services.llm import stream_reply


UPSTREAM_PATH = "/v1/chat/completions"
FALLBACK_REPLY = "The language model is currently unavailable. Please try again in a moment."


def _sse_body(*lines):
    """Build a raw SSE response body from a sequence of `data:` payloads.

    Each item is either a dict (JSON-encoded) or the literal string
    "[DONE]" for the sentinel line.
    """
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


# ---------------------------------------------------------------------------
# AC-2: request shape
# ---------------------------------------------------------------------------

def test_request_carries_model_user_message_and_stream_true(monkeypatch, httpserver):
    _configure_env(monkeypatch, httpserver)
    httpserver.expect_request(UPSTREAM_PATH, method="POST").respond_with_data(
        _sse_body(_delta("hi"), "[DONE]"),
        content_type="text/event-stream",
    )

    list(stream_reply("hello there"))

    request = httpserver.log[0][0]
    sent = json.loads(request.get_data(as_text=True))
    assert sent["model"] == "test-model"
    assert sent["stream"] is True
    assert sent["messages"][-1] == {"role": "user", "content": "hello there"}


# ---------------------------------------------------------------------------
# AC-3 / AC-4: system prompt inclusion
# ---------------------------------------------------------------------------

def test_system_prompt_included_when_set(monkeypatch, httpserver):
    _configure_env(monkeypatch, httpserver)
    monkeypatch.setenv("LLM_SYSTEM_PROMPT", "be terse")
    httpserver.expect_request(UPSTREAM_PATH, method="POST").respond_with_data(
        _sse_body(_delta("ok"), "[DONE]"),
        content_type="text/event-stream",
    )

    list(stream_reply("hi"))

    request = httpserver.log[0][0]
    sent = json.loads(request.get_data(as_text=True))
    assert sent["messages"][0] == {"role": "system", "content": "be terse"}


def test_system_prompt_omitted_when_empty(monkeypatch, httpserver):
    _configure_env(monkeypatch, httpserver)  # LLM_SYSTEM_PROMPT == ""
    httpserver.expect_request(UPSTREAM_PATH, method="POST").respond_with_data(
        _sse_body(_delta("ok"), "[DONE]"),
        content_type="text/event-stream",
    )

    list(stream_reply("hi"))

    request = httpserver.log[0][0]
    sent = json.loads(request.get_data(as_text=True))
    assert all(m["role"] != "system" for m in sent["messages"])


# ---------------------------------------------------------------------------
# AC-5 / AC-6: token/done sequencing on the happy path
# ---------------------------------------------------------------------------

def test_content_chunks_yielded_as_tokens_in_order(monkeypatch, httpserver):
    _configure_env(monkeypatch, httpserver)
    httpserver.expect_request(UPSTREAM_PATH, method="POST").respond_with_data(
        _sse_body(_delta("Hel"), _delta("lo"), _delta(" world"), "[DONE]"),
        content_type="text/event-stream",
    )

    chunks = list(stream_reply("hi"))

    tokens = [c for c in chunks if c[0] == "token"]
    assert [c[1] for c in tokens] == ["Hel", "lo", " world"]


def test_clean_completion_yields_done(monkeypatch, httpserver):
    _configure_env(monkeypatch, httpserver)
    httpserver.expect_request(UPSTREAM_PATH, method="POST").respond_with_data(
        _sse_body(_delta("hi"), "[DONE]"),
        content_type="text/event-stream",
    )

    chunks = list(stream_reply("hi"))

    assert chunks[-1] == ("done",)
    assert chunks.count(("done",)) == 1
    assert not any(c[0] == "error" for c in chunks)


# ---------------------------------------------------------------------------
# AC-7: clean but empty completion is a failure, not an empty success
# ---------------------------------------------------------------------------

def test_empty_stream_yields_error_not_done(monkeypatch, httpserver):
    _configure_env(monkeypatch, httpserver)
    httpserver.expect_request(UPSTREAM_PATH, method="POST").respond_with_data(
        _sse_body("[DONE]"),
        content_type="text/event-stream",
    )

    chunks = list(stream_reply("hi"))

    assert chunks == [("error",)]


# ---------------------------------------------------------------------------
# AC-8: late-bound config
# ---------------------------------------------------------------------------

def test_config_read_at_call_time(monkeypatch, httpserver):
    # First call: point at nothing listening -> pre-stream error.
    monkeypatch.setenv("LLM_ENDPOINT", "http://127.0.0.1:1/v1/chat/completions")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("LLM_SYSTEM_PROMPT", "")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "2")

    first = list(stream_reply("hi"))
    assert first == [("error",)]

    # Re-point the env var, same process, no re-import -> should now succeed.
    httpserver.expect_request(UPSTREAM_PATH, method="POST").respond_with_data(
        _sse_body(_delta("hi"), "[DONE]"),
        content_type="text/event-stream",
    )
    monkeypatch.setenv("LLM_ENDPOINT", httpserver.url_for(UPSTREAM_PATH))

    second = list(stream_reply("hi"))
    assert second[-1] == ("done",)
    assert any(c[0] == "token" for c in second)


# ---------------------------------------------------------------------------
# AC-9: connection failure, pre-stream
# ---------------------------------------------------------------------------

def test_connection_error_yields_error_with_no_tokens(monkeypatch):
    monkeypatch.setenv("LLM_ENDPOINT", "http://127.0.0.1:1/v1/chat/completions")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("LLM_SYSTEM_PROMPT", "")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "2")

    chunks = list(stream_reply("hi"))

    assert chunks == [("error",)]


# ---------------------------------------------------------------------------
# AC-10: non-2xx, pre-stream
# ---------------------------------------------------------------------------

def test_non_2xx_yields_error_with_no_tokens(monkeypatch, httpserver):
    _configure_env(monkeypatch, httpserver)
    httpserver.expect_request(UPSTREAM_PATH, method="POST").respond_with_data(
        "internal error", status=500,
    )

    chunks = list(stream_reply("hi"))

    assert chunks == [("error",)]


# ---------------------------------------------------------------------------
# AC-11: no first byte within LLM_TIMEOUT_SECONDS
# ---------------------------------------------------------------------------

def test_timeout_to_first_byte_yields_error(monkeypatch, httpserver):
    _configure_env(monkeypatch, httpserver, timeout="1")

    def slow_handler(request):
        time.sleep(2)
        return Response(
            _sse_body(_delta("late"), "[DONE]"),
            content_type="text/event-stream",
        )

    httpserver.expect_request(UPSTREAM_PATH, method="POST").respond_with_handler(slow_handler)

    chunks = list(stream_reply("hi"))

    assert chunks == [("error",)]


# ---------------------------------------------------------------------------
# AC-12: mid-stream drop / malformed data after tokens already emitted
# ---------------------------------------------------------------------------

def test_mid_stream_drop_yields_error_after_tokens(monkeypatch, httpserver):
    _configure_env(monkeypatch, httpserver)
    body = b"data: " + json.dumps(_delta("Hello")).encode("utf-8") + b"\n\n" + b"data: not-json\n\n"
    httpserver.expect_request(UPSTREAM_PATH, method="POST").respond_with_data(
        body, content_type="text/event-stream",
    )

    chunks = list(stream_reply("hi"))

    assert chunks[0] == ("token", "Hello")
    assert chunks[-1] == ("error",)
    assert not any(c == ("done",) for c in chunks)
