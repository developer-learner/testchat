"""M8 threads routes — snapshot API (AC-36/AC-37).

M24 (AC-79): the GET response carries a quarantined flag so the UI can
surface an unreadable-history event (the response shape gained one field;
the exact-shape asserts below were amended in the same freeze).
"""
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
    assert r.json() == {"threads": [], "quarantined": False}


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
    assert client.get("/api/v1/threads").json() == {"threads": [], "quarantined": False}


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
    assert r.json() == {"threads": [], "quarantined": False}


# AC-79 [M24 — unreadable history is reported, not hidden]
def test_get_reports_quarantine_after_corrupt_snapshot(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    data = tmp_path / "threads.json"
    data.write_text("{not valid json!!")
    r = client.get("/api/v1/threads")
    assert r.status_code == 200
    assert r.json() == {"threads": [], "quarantined": True}
    # flag is quarantine-file-based: it survives further requests
    assert client.get("/api/v1/threads").json()["quarantined"] is True
    assert len(list(tmp_path.glob("threads.json.corrupt-*"))) == 1
