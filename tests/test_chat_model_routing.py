"""
Oracle for M5 AC-9 through AC-12: model-based routing on POST /api/v1/chat.
Observes ONLY contracts.entry_points (src.main:app, src.services.llm:stream_reply,
src.services.models:*) and contracts.routes (POST /api/v1/chat).
"""

import pytest
from fastapi.testclient import TestClient

from src.main import app
import src.services.models as models_mod
import src.services.llm as llm_mod
import src.api.chat as chat_mod


@pytest.fixture(autouse=True)
def _reset_nemotron_state():
    models_mod._nemotron_process = None
    yield
    models_mod._nemotron_process = None


@pytest.fixture
def client():
    return TestClient(app)


def _patch_nemotron_loaded(monkeypatch, value: bool):
    """chat.py routes loaded-checks through the models module's
    is_script_model_loaded, which delegates nemotron to is_nemotron_loaded."""
    monkeypatch.setattr(models_mod, "is_nemotron_loaded", lambda: value)


def _patch_deepseek_loaded(monkeypatch, value: bool):
    monkeypatch.setattr(
        chat_mod, "is_script_model_loaded", lambda model_id: value
    )


def test_chat_routes_to_nemotron_and_passes_model(client, monkeypatch):
    _patch_nemotron_loaded(monkeypatch, True)

    captured = {}

    def fake_stream_reply(message, history=(), endpoint_override=None, model=None):
        captured["endpoint_override"] = endpoint_override
        captured["model"] = model
        yield ("token", "hi")
        yield ("done",)

    monkeypatch.setattr(llm_mod, "stream_reply", fake_stream_reply)

    resp = client.post("/api/v1/chat", json={"message": "hello", "model": "nemotron"})

    assert resp.status_code == 200
    assert captured["endpoint_override"] == models_mod.NEMOTRON_CHAT_ENDPOINT
    assert captured["model"] == "nemotron"


def test_chat_routes_to_lmstudio_and_passes_model(client, monkeypatch):
    captured = {}

    def fake_stream_reply(message, history=(), endpoint_override=None, model=None):
        captured["endpoint_override"] = endpoint_override
        captured["model"] = model
        yield ("token", "hi")
        yield ("done",)

    monkeypatch.setattr(llm_mod, "stream_reply", fake_stream_reply)

    resp = client.post("/api/v1/chat", json={"message": "hello"})
    assert resp.status_code == 200
    assert captured["endpoint_override"] is None
    assert captured["model"] is None

    captured.clear()
    resp2 = client.post(
        "/api/v1/chat", json={"message": "hello", "model": "qwen/qwen3.6-27b"}
    )
    assert resp2.status_code == 200
    assert captured["endpoint_override"] is None
    assert captured["model"] == "qwen/qwen3.6-27b"


def test_chat_invalid_model_type_is_422(client):
    resp = client.post("/api/v1/chat", json={"message": "hello", "model": 123})
    assert resp.status_code == 422


def test_chat_nemotron_selected_but_not_loaded_is_422(client, monkeypatch):
    _patch_nemotron_loaded(monkeypatch, False)

    resp = client.post("/api/v1/chat", json={"message": "hello", "model": "nemotron"})

    assert resp.status_code == 422


def test_chat_routes_to_deepseek_and_passes_model(client, monkeypatch):
    _patch_deepseek_loaded(monkeypatch, True)

    captured = {}

    def fake_stream_reply(message, history=(), endpoint_override=None, model=None):
        captured["endpoint_override"] = endpoint_override
        captured["model"] = model
        yield ("token", "hi")
        yield ("done",)

    monkeypatch.setattr(llm_mod, "stream_reply", fake_stream_reply)

    resp = client.post(
        "/api/v1/chat", json={"message": "hello", "model": "deepseek-v4-flash"}
    )

    assert resp.status_code == 200
    assert captured["endpoint_override"] == models_mod.DEEPSEEK_CHAT_ENDPOINT
    assert captured["model"] == "deepseek-v4-flash"


def test_chat_deepseek_selected_but_not_loaded_is_422(client, monkeypatch):
    _patch_deepseek_loaded(monkeypatch, False)

    resp = client.post(
        "/api/v1/chat", json={"message": "hello", "model": "deepseek-v4-flash"}
    )

    assert resp.status_code == 422


def test_chat_routes_to_deepseek_0731_and_preserves_id(client, monkeypatch):
    model_id = "deepseek-v4-flash-0731"
    monkeypatch.setattr(
        chat_mod,
        "is_script_model_loaded",
        lambda candidate: candidate == model_id,
    )
    captured = {}

    def fake_stream_reply(message, history=(), endpoint_override=None, model=None):
        captured["endpoint_override"] = endpoint_override
        captured["model"] = model
        yield ("token", "hi")
        yield ("done",)

    monkeypatch.setattr(llm_mod, "stream_reply", fake_stream_reply)

    resp = client.post(
        "/api/v1/chat", json={"message": "hello", "model": model_id}
    )

    assert resp.status_code == 200
    assert captured["endpoint_override"] == (
        models_mod.get_script_model(model_id)["chat_endpoint"]
    )
    assert captured["model"] == model_id


def test_chat_deepseek_0731_selected_but_not_loaded_is_422(
    client, monkeypatch
):
    model_id = "deepseek-v4-flash-0731"
    monkeypatch.setattr(chat_mod, "is_script_model_loaded", lambda _: False)

    called = False

    def should_not_stream(*args, **kwargs):
        nonlocal called
        called = True
        yield ("done",)

    monkeypatch.setattr(llm_mod, "stream_reply", should_not_stream)

    resp = client.post(
        "/api/v1/chat", json={"message": "hello", "model": model_id}
    )

    assert resp.status_code == 422
    assert called is False
