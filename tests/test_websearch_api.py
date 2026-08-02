"""Oracle tests for the M25 web-informed chat path and its neighbors.

Surface gate (INV-4): src.main:app only from src. Routes from
contracts.routes. The Tavily stub and LLM stub share one pytest
HTTPServer on distinct paths; shapes derive from
captures/tavily-search.json and captures/lmstudio-chat-stream.txt (D-56).
"""
import json

from fastapi.testclient import TestClient
from pytest_httpserver import HTTPServer

from src.main import app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sse_chunk(content: str) -> str:
    obj = {"choices": [{"delta": {"content": content}}]}
    return f"data: {json.dumps(obj)}\n\n"


def _make_sse_body(*contents: str) -> str:
    return "".join(_sse_chunk(c) for c in contents) + "data: [DONE]\n\n"


def _tavily_payload() -> dict:
    # shape: captures/tavily-search.json
    return {
        "query": "q",
        "follow_up_questions": None,
        "answer": None,
        "images": [],
        "results": [
            {
                "url": "https://example.org/one",
                "title": "One",
                "content": "first fact",
                "score": 0.9,
                "raw_content": None,
            },
            {
                "url": "https://example.org/two",
                "title": "Two",
                "content": "second fact",
                "score": 0.8,
                "raw_content": None,
            },
        ],
        "response_time": 0.5,
        "request_id": "test",
    }


def _setup_env(monkeypatch, httpserver: HTTPServer) -> None:
    monkeypatch.setenv("LLM_ENDPOINT", httpserver.url_for("/v1/chat/completions"))
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("LLM_SYSTEM_PROMPT", "")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "5")
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    monkeypatch.setenv("TAVILY_ENDPOINT", httpserver.url_for("/search"))


def _expect_llm(httpserver: HTTPServer, body: str) -> None:
    httpserver.expect_request(
        "/v1/chat/completions", method="POST"
    ).respond_with_data(body, status=200, content_type="text/event-stream")


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


def _search_requests(httpserver: HTTPServer) -> list:
    return [entry for entry in httpserver.log if entry[0].path == "/search"]


def _llm_message(httpserver: HTTPServer) -> str:
    llm_entries = [
        entry for entry in httpserver.log if entry[0].path == "/v1/chat/completions"
    ]
    assert llm_entries, "LLM endpoint was never called"
    body = json.loads(llm_entries[-1][0].data)
    return body["messages"][-1]["content"]


# ---------------------------------------------------------------------------
# AC-90 — status advertises configuration
# ---------------------------------------------------------------------------


def test_status_reports_web_configured(monkeypatch):
    client = TestClient(app, raise_server_exceptions=False)
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    assert client.get("/api/v1/status").json()["web_configured"] is True
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    assert client.get("/api/v1/status").json()["web_configured"] is False


# ---------------------------------------------------------------------------
# AC-85/86/87/89 — the chat path
# ---------------------------------------------------------------------------


def test_web_false_issues_no_search(monkeypatch, httpserver: HTTPServer):
    _setup_env(monkeypatch, httpserver)
    _expect_llm(httpserver, _make_sse_body("hi"))
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/api/v1/chat", json={"message": "Hello"})
    assert resp.status_code == 200
    assert _search_requests(httpserver) == []
    events = _parse_sse_events(resp.text)
    assert all(e["event"] != "sources" for e in events)
    assert _llm_message(httpserver) == "Hello"


def test_web_true_emits_sources_before_tokens(monkeypatch, httpserver: HTTPServer):
    _setup_env(monkeypatch, httpserver)
    httpserver.expect_request("/search", method="POST").respond_with_json(
        _tavily_payload()
    )
    _expect_llm(httpserver, _make_sse_body("informed reply"))
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/api/v1/chat", json={"message": "what is new", "web": True})
    assert resp.status_code == 200
    events = _parse_sse_events(resp.text)
    kinds = [e["event"] for e in events]
    assert "sources" in kinds and "token" in kinds
    assert kinds.index("sources") < kinds.index("token")
    src = next(e for e in events if e["event"] == "sources")["data"]["sources"]
    assert [s["n"] for s in src] == [1, 2]
    assert src[0]["url"] == "https://example.org/one"
    assert src[0]["title"] == "One"


def test_web_true_augments_prompt(monkeypatch, httpserver: HTTPServer):
    _setup_env(monkeypatch, httpserver)
    httpserver.expect_request("/search", method="POST").respond_with_json(
        _tavily_payload()
    )
    _expect_llm(httpserver, _make_sse_body("informed reply"))
    client = TestClient(app, raise_server_exceptions=False)
    client.post("/api/v1/chat", json={"message": "what is new", "web": True})
    sent = _llm_message(httpserver)
    assert "[1] One" in sent
    assert "[2] Two" in sent
    assert "first fact" in sent
    assert sent.rstrip().endswith("what is new")
    search_body = json.loads(_search_requests(httpserver)[-1][0].data)
    assert search_body["query"] == "what is new"


def test_search_failure_falls_back_with_notice(monkeypatch, httpserver: HTTPServer):
    _setup_env(monkeypatch, httpserver)
    httpserver.expect_request("/search", method="POST").respond_with_data(
        "boom", status=500
    )
    _expect_llm(httpserver, _make_sse_body("plain reply"))
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/api/v1/chat", json={"message": "what is new", "web": True})
    assert resp.status_code == 200
    events = _parse_sse_events(resp.text)
    src = next(e for e in events if e["event"] == "sources")["data"]
    assert src["sources"] == []
    assert src["notice"] == "web search unavailable"
    assert any(e["event"] == "token" for e in events)
    assert _llm_message(httpserver) == "what is new"


# ---------------------------------------------------------------------------
# AC-91 — persistence round-trips sources; sourceless shape unchanged
# ---------------------------------------------------------------------------


def test_put_threads_roundtrips_sources(monkeypatch, tmp_path):
    monkeypatch.setenv("TESTCHAT_DATA", str(tmp_path / "threads.json"))
    client = TestClient(app, raise_server_exceptions=False)
    payload = {
        "threads": [
            {
                "id": 1,
                "title": "t",
                "model": "",
                "locked": False,
                "messages": [
                    {"role": "user", "content": "q", "ts": 1.0, "model": ""},
                    {
                        "role": "assistant",
                        "content": "a",
                        "ts": 2.0,
                        "model": "m",
                        "sources": [
                            {"title": "One", "url": "https://example.org/one"}
                        ],
                    },
                ],
            }
        ]
    }
    payload["revision"] = client.get("/api/v1/threads").json()["revision"]
    assert client.put("/api/v1/threads", json=payload).status_code == 200
    messages = client.get("/api/v1/threads").json()["threads"][0]["messages"]
    assert messages[1]["sources"] == [
        {"title": "One", "url": "https://example.org/one"}
    ]
    assert "sources" not in messages[0]
