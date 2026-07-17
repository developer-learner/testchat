"""Oracle tests for src/services/websearch.py — M25 web-informed answers.

Surface gate (INV-4): imports only from contracts.entry_points
(src.services.websearch and its names). Response shapes derive from
captures/tavily-search.json (D-56): top-level results[] of
{url, title, content, score, raw_content}.
"""
import json

import pytest
from pytest_httpserver import HTTPServer

from src.services.websearch import (
    WebSearchError,
    build_prompt,
    is_configured,
    search_web,
)

# ---------------------------------------------------------------------------
# Helpers — capture-shaped payloads
# ---------------------------------------------------------------------------


def _tavily_result(i: int, content: str = "extracted prose") -> dict:
    # shape: captures/tavily-search.json results[] entries
    return {
        "url": f"https://example.org/page-{i}",
        "title": f"Result {i}",
        "content": content,
        "score": 0.9 - i * 0.1,
        "raw_content": None,
    }


def _tavily_payload(n: int, content: str = "extracted prose") -> dict:
    return {
        "query": "q",
        "follow_up_questions": None,
        "answer": None,
        "images": [],
        "results": [_tavily_result(i, content) for i in range(1, n + 1)],
        "response_time": 0.5,
        "request_id": "test",
    }


def _setup_env(monkeypatch, httpserver: HTTPServer) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    monkeypatch.setenv("TAVILY_ENDPOINT", httpserver.url_for("/search"))


# ---------------------------------------------------------------------------
# AC-90 — configuration gate
# ---------------------------------------------------------------------------


def test_unconfigured_when_key_missing(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    assert is_configured() is False
    with pytest.raises(WebSearchError):
        search_web("anything")


def test_configured_with_key(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    assert is_configured() is True


# ---------------------------------------------------------------------------
# AC-86/87 — request and response handling
# ---------------------------------------------------------------------------


def test_search_sends_bearer_and_query(monkeypatch, httpserver: HTTPServer):
    _setup_env(monkeypatch, httpserver)
    httpserver.expect_request("/search", method="POST").respond_with_json(
        _tavily_payload(2)
    )
    sources = search_web("what is new today")
    assert len(sources) == 2
    req = httpserver.log[-1][0]
    assert req.headers.get("Authorization") == "Bearer test-key"
    body = json.loads(req.data)
    assert body["query"] == "what is new today"


def test_search_returns_at_most_four_sources(monkeypatch, httpserver: HTTPServer):
    _setup_env(monkeypatch, httpserver)
    httpserver.expect_request("/search", method="POST").respond_with_json(
        _tavily_payload(6)
    )
    sources = search_web("q")
    assert len(sources) == 4
    for s in sources:
        assert set(s.keys()) == {"title", "url", "content"}
        assert s["url"].startswith("https://example.org/")


def test_source_content_capped(monkeypatch, httpserver: HTTPServer):
    _setup_env(monkeypatch, httpserver)
    httpserver.expect_request("/search", method="POST").respond_with_json(
        _tavily_payload(1, content="x" * 5000)
    )
    sources = search_web("q")
    assert len(sources[0]["content"]) == 2000


def test_search_http_error_raises(monkeypatch, httpserver: HTTPServer):
    _setup_env(monkeypatch, httpserver)
    httpserver.expect_request("/search", method="POST").respond_with_data(
        "upstream sad", status=500
    )
    with pytest.raises(WebSearchError):
        search_web("q")


# ---------------------------------------------------------------------------
# AC-87 — prompt structure (the weak-model contract: numbered, bounded,
# question last)
# ---------------------------------------------------------------------------


def test_build_prompt_numbers_sources_and_keeps_question():
    sources = [
        {"title": "Alpha", "url": "https://a.example", "content": "alpha facts"},
        {"title": "Beta", "url": "https://b.example", "content": "beta facts"},
    ]
    prompt = build_prompt("what changed?", sources)
    assert "[1] Alpha" in prompt
    assert "[2] Beta" in prompt
    assert "https://a.example" in prompt
    assert "alpha facts" in prompt
    assert prompt.rstrip().endswith("what changed?")
    assert prompt.index("[1]") < prompt.index("[2]") < prompt.index("what changed?")


# ---------------------------------------------------------------------------
# AC-93 (M26 ratify) — the prompt must instruct plain-bracket citations and
# specific/recent-number preference; a live Qwen reply used 【N†…】 markers
# and picked a stale point-release even though the current one was in the
# sources, so the prompt now nudges both.
# ---------------------------------------------------------------------------


def test_prompt_forbids_full_width_citations():
    prompt = build_prompt("q", [{"title": "A", "url": "https://a", "content": "x"}])
    lowered = prompt.lower()
    assert "[1]" in prompt
    # instruction must explicitly name the plain-bracket form
    assert "[n]" in lowered or "[1] or [2]" in lowered or "plain square" in lowered
    # and nudge toward the freshest/most-specific number when sources differ
    assert "specific" in lowered or "recent" in lowered
    # explicitly reject the Chinese full-width marker in the emitted prompt
    assert "【" not in prompt and "】" not in prompt  # 【 】
