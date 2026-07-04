"""API tests for POST /api/v1/chat (src/api/chat.py via the composed app).

Pins AC-3, AC-4, AC-5. Observes only the locked entry point `src.main:app`
and the locked route `POST /api/v1/chat`.
"""
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_chat_echoes_message():
    # AC-3: a normal message round-trips as {"reply": "Echo: <message>"}.
    r = client.post("/api/v1/chat", json={"message": "hello"})
    assert r.status_code == 200
    assert r.json() == {"reply": "Echo: hello"}


def test_chat_empty_message_echoed():
    # AC-4: empty message is valid and echoes as {"reply": "Echo: "}.
    r = client.post("/api/v1/chat", json={"message": ""})
    assert r.status_code == 200
    assert r.json() == {"reply": "Echo: "}


def test_chat_missing_message_is_validation_error():
    # AC-5: omitting the required "message" field is a 422 validation error.
    r = client.post("/api/v1/chat", json={})
    assert r.status_code == 422
