"""
Oracle for M5 AC-9 through AC-12: model-based routing on POST /api/v1/chat.
Observes ONLY contracts.entry_points (src.main:app, src.services.llm:stream_reply,
src.services.models:*) and contracts.routes (POST /api/v1/chat).
"""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.main import app
import src.services.models as models_mod
import src.services.llm as llm_mod


@pytest.fixture(autouse=True)
def _reset_nemotron_state():
    models_mod._nemotron_process = None
    yield
    models_mod._nemotron_process = None


@pytest.fixture
def client():
    return TestClient(app)


def test_chat_routes_to_nemotron_when_selected(client, monkeypatch):
    fake_proc = MagicMock()
    fake_proc.poll.return_value = None
    models_mod._nemotron_process = fake_proc

    captured = {}

    def fake_stream_reply(message, history=(), endpoint_override=None):
        captured["endpoint_override"] = endpoint_override
        yield ("token", "hi")
        yield ("done",)

    monkeypatch.setattr(llm_mod, "stream_reply", fake_stream_reply)

    resp = client.post("/api/v1/chat", json={"message": "hello", "model": "nemotron"})

    assert resp.status_code == 200
    assert captured["endpoint_override"] == models_mod.NEMOTRON_CHAT_ENDPOINT


def test_chat_routes_to_lmstudio_when_model_absent_or_other(client, monkeypatch):
    captured = {}

    def fake_stream_reply(message, history=(), endpoint_override=None):
        captured["endpoint_override"] = endpoint_override
        yield ("token", "hi")
        yield ("done",)

    monkeypatch.setattr(llm_mod, "stream_reply", fake_stream_reply)

    resp = client.post("/api/v1/chat", json={"message": "hello"})
    assert resp.status_code == 200
    assert captured["endpoint_override"] is None

    resp2 = client.post(
        "/api/v1/chat", json={"message": "hello", "model": "some-lmstudio-model"}
    )
    assert resp2.status_code == 200
    assert captured["endpoint_override"] is None


def test_chat_invalid_model_type_is_422(client):
    resp = client.post("/api/v1/chat", json={"message": "hello", "model": 123})
    assert resp.status_code == 422


def test_chat_nemotron_selected_but_not_loaded_is_422(client):
    models_mod._nemotron_process = None

    resp = client.post("/api/v1/chat", json={"message": "hello", "model": "nemotron"})

    assert resp.status_code == 422
