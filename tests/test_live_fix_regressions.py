"""Regression oracles for the 2026-09-23 direct fixes (AC-205..AC-207).

The fixes landed directly (D-132) without tests, because tests can only enter
through a freeze (INV-1). These pin them: a chat request's blocking pre-stream
checks must not stall the server, a chunk without choices must not end a
reply, and the RAM readout must find an externally started model server by its
listening port, never by process name.
"""
import json
import threading
import time

from fastapi.testclient import TestClient
from pytest_httpserver import HTTPServer

import src.api.chat as chat_mod
import src.api.status as status_mod
from src.main import app
from src.services.llm import stream_reply


# AC-205 — other requests keep being served while a chat waits on its checks.
def test_chat_precheck_does_not_stall_other_requests(monkeypatch) -> None:
    entered = threading.Event()
    release = threading.Event()

    def slow_loaded_check(model_id: str) -> bool:
        entered.set()
        release.wait(timeout=10)
        return False

    monkeypatch.setattr(
        chat_mod, "get_script_model", lambda model_id: {"chat_endpoint": "http://127.0.0.1:9/x"}
    )
    monkeypatch.setattr(chat_mod, "is_script_model_loaded", slow_loaded_check)

    with TestClient(app) as client:
        chat_result: dict[str, int] = {}

        def send_chat() -> None:
            response = client.post(
                "/api/v1/chat", json={"message": "hi", "model": "some-script-model"}
            )
            chat_result["status"] = response.status_code

        worker = threading.Thread(target=send_chat)
        worker.start()
        assert entered.wait(timeout=10), "chat never reached its pre-stream check"

        started = time.monotonic()
        settings = client.get("/api/v1/settings")
        elapsed = time.monotonic() - started

        release.set()
        worker.join(timeout=10)

    assert settings.status_code == 200
    assert elapsed < 2.0, f"settings waited {elapsed:.2f}s behind a blocked chat check"
    assert chat_result["status"] == 422


# AC-206 — a chunk with no choices is skipped; the reply completes.
def test_stream_skips_a_chunk_without_choices(monkeypatch, httpserver: HTTPServer) -> None:
    body = (
        f'data: {json.dumps({"choices": [{"delta": {"content": "Hello"}}]})}\n\n'
        f'data: {json.dumps({"choices": [], "usage": {"total_tokens": 3}})}\n\n'
        f'data: {json.dumps({"choices": [{"delta": {"content": " world"}}]})}\n\n'
        "data: [DONE]\n\n"
    )
    httpserver.expect_request("/v1/chat/completions", method="POST").respond_with_data(
        body, content_type="text/event-stream"
    )
    monkeypatch.setenv("LLM_ENDPOINT", httpserver.url_for("/v1/chat/completions"))
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "5")

    items = list(stream_reply("hi", []))

    tokens = "".join(item[1] for item in items if item[0] == "token")
    assert tokens == "Hello world"
    assert not [item for item in items if item[0] == "error"]
    assert items[-1][0] == "done"


# AC-207 — an externally started server is found by its port, not its name.
def test_ram_readout_finds_external_server_by_listening_port(monkeypatch) -> None:
    ports_asked: list[int] = []
    commands_run: list[list[str]] = []

    def find_listening_pid(port: int):
        ports_asked.append(port)
        return 4242 if port == 8600 else None

    def run(argv, **kwargs):
        commands_run.append(list(argv))

        class Result:
            stdout = "2097152\n" if argv[:1] == ["ps"] and "4242" in argv else "999\n"

        return Result()

    monkeypatch.setattr(status_mod.models_service, "_get_process", lambda model_id: None)
    monkeypatch.setattr(
        status_mod.models_service,
        "get_script_model",
        lambda model_id: {
            "ready_url": "http://127.0.0.1:8600/v1/models",
            "command": ["python", "/opt/models/serve_nemotron.py"],
        },
    )
    monkeypatch.setattr(status_mod.models_service, "_find_listening_pid", find_listening_pid)
    monkeypatch.setattr(status_mod.subprocess, "run", run)

    rss_gb = status_mod._script_model_rss_gb("nemotron")

    assert ports_asked == [8600]
    assert rss_gb == 2.0
    assert not [cmd for cmd in commands_run if cmd[:1] == ["pgrep"]]
