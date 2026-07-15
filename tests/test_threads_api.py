"""M8 threads routes — snapshot API (AC-36/AC-37)."""
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)

PAYLOAD = {"threads": [
    {"id": 1, "title": "First chat", "messages": [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "Hello there"},
    ], "model": "alpha-model", "locked": True},
]}


def _isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("TESTCHAT_DATA", str(tmp_path / "threads.json"))


def test_get_with_no_saved_data_returns_empty(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    r = client.get("/api/v1/threads")
    assert r.status_code == 200
    assert r.json() == {"threads": []}


def test_put_then_get_roundtrips(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    r = client.put("/api/v1/threads", json=PAYLOAD)
    assert r.status_code == 200
    r = client.get("/api/v1/threads")
    assert r.status_code == 200
    assert r.json()["threads"][0]["title"] == "First chat"
    assert r.json()["threads"][0]["locked"] is True
    assert r.json()["threads"][0]["messages"][1]["content"] == "Hello there"


def test_put_malformed_payload_is_422_and_preserves_stored(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    client.put("/api/v1/threads", json=PAYLOAD)
    r = client.put("/api/v1/threads", json={"threads": [{"bogus": True}]})
    assert r.status_code == 422
    assert client.get("/api/v1/threads").json()["threads"][0]["title"] == "First chat"


def test_delete_clears_snapshot(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    client.put("/api/v1/threads", json=PAYLOAD)
    r = client.delete("/api/v1/threads")
    assert r.status_code == 200
    assert client.get("/api/v1/threads").json() == {"threads": []}


def test_optional_fields_default(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    minimal = {"threads": [{"id": 3, "title": "New Chat", "messages": []}]}
    assert client.put("/api/v1/threads", json=minimal).status_code == 200
    saved = client.get("/api/v1/threads").json()["threads"][0]
    assert saved["model"] == ""
    assert saved["locked"] is False


def test_put_invalid_role_rejected(tmp_path, monkeypatch):
    # AC-77: roles outside user/assistant are rejected and nothing persists
    _isolate(tmp_path, monkeypatch)
    bad = {"threads": [{"id": 1, "title": "x", "messages": [
        {"role": "system", "content": "sneaky"}], "model": "", "locked": False}]}
    r = client.put("/api/v1/threads", json=bad)
    assert r.status_code == 422
    r = client.get("/api/v1/threads")
    assert r.json() == {"threads": []}
