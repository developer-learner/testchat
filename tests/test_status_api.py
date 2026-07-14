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


# AC-60/AC-61 [M17 — loadable-memory estimate]
def test_status_reports_loadable_gb():
    body = client.get("/api/v1/status").json()
    assert "loadable_gb" in body, "payload must carry the loadable estimate"
    loadable = body["loadable_gb"]
    assert isinstance(loadable, (int, float))
    assert loadable >= 0.0, "loadable estimate is floored at zero"
    if body.get("ram_total_gb", 0) > 0:
        assert loadable <= body["ram_total_gb"], (
            "cannot load more than the machine has"
        )


def test_status_existing_fields_survive():
    # AC additive guarantee — the M10 surface is untouched
    body = client.get("/api/v1/status").json()
    for key in ("nemotron_loaded", "nemotron_rss_gb", "ram_used_gb", "ram_total_gb"):
        assert key in body, f"pre-M17 field {key} must remain"
