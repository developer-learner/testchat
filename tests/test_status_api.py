"""M10 status — the UI status strip's data source (AC-52)."""
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_status_returns_json_object():
    r = client.get("/api/v1/status")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, dict)
    assert body, "status payload must not be empty"


def test_status_is_repeatable():
    # the strip polls this endpoint — two consecutive calls both succeed
    assert client.get("/api/v1/status").status_code == 200
    assert client.get("/api/v1/status").status_code == 200
