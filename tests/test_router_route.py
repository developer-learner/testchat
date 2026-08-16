"""
Oracle for spec v107 AC-170..AC-174: the router model (dual-path through the
vortex universal surface). Observes ONLY contracts.entry_points
(src.main:app, src.services.models module + the new router seams,
src.services.llm:stream_reply) and contracts.routes (POST /api/v1/chat,
GET /api/v1/models, GET /api/v1/models/catalog). The router endpoint is
simulated with pytest-httpserver; no live vortex required.

AC-170: router model present in GET /api/v1/models when the router lists it.
AC-171: omitted from the list when the probe fails / omits it; never in the
        catalog, so the script-model load/unload machinery stays uninvolved.
AC-172: router-model chat streams from {VORTEX_URL}/v1/chat/completions with
        the model id passed through.
AC-173: router-model chat with the router not listing it is 422 pre-stream.
AC-174: VORTEX_URL unset -> no router model, no probe, generic path unchanged.
"""

import pytest
from fastapi.testclient import TestClient

from src.main import app
import src.services.models as models_mod
import src.services.llm as llm_mod


@pytest.fixture
def client():
    return TestClient(app)


def _router_base(httpserver) -> str:
    """Base URL of the simulated router (no trailing slash)."""
    return httpserver.url_for("/").rstrip("/")


def _serve_router_models(httpserver, ids):
    """Simulate the vortex universal surface's GET /v1/models."""
    httpserver.expect_request("/v1/models").respond_with_json(
        {
            "object": "list",
            "data": [
                {"id": model_id, "object": "model"} for model_id in ids
            ],
        }
    )


def _patch_stream_reply(monkeypatch, captured):
    def fake_stream_reply(message, history=(), endpoint_override=None, model=None):
        captured["endpoint_override"] = endpoint_override
        captured["model"] = model
        yield ("token", "hi")
        yield ("done",)

    monkeypatch.setattr(llm_mod, "stream_reply", fake_stream_reply)


# --- router_models() ---------------------------------------------------------


def test_router_models_lists_router_when_router_reports_it(monkeypatch, httpserver):
    _serve_router_models(httpserver, ["other-model", models_mod.ROUTER_MODEL_ID])
    monkeypatch.setenv("VORTEX_URL", _router_base(httpserver))

    assert models_mod.router_models() == [
        {"id": models_mod.ROUTER_MODEL_ID, "source": "router"}
    ]


def test_router_models_empty_when_router_omits_it(monkeypatch, httpserver):
    _serve_router_models(httpserver, ["other-model"])
    monkeypatch.setenv("VORTEX_URL", _router_base(httpserver))

    assert models_mod.router_models() == []


def test_router_models_empty_when_router_503(monkeypatch, httpserver):
    httpserver.expect_request("/v1/models").respond_with_json(
        {"error": "unavailable"}, status=503
    )
    monkeypatch.setenv("VORTEX_URL", _router_base(httpserver))

    assert models_mod.router_models() == []


def test_router_models_empty_when_probe_raises(monkeypatch):
    monkeypatch.setenv("VORTEX_URL", "http://127.0.0.1:1")

    def _raise(*args, **kwargs):
        raise models_mod.httpx.ConnectError("connection refused")

    monkeypatch.setattr(models_mod.httpx, "get", _raise)

    assert models_mod.router_models() == []


def test_router_models_empty_when_vortex_url_unset(monkeypatch):
    monkeypatch.delenv("VORTEX_URL", raising=False)

    def _raise(*args, **kwargs):
        raise AssertionError("router probe must not run with VORTEX_URL unset")

    monkeypatch.setattr(models_mod.httpx, "get", _raise)

    assert models_mod.router_models() == []


def test_is_router_configured_reflects_env(monkeypatch):
    monkeypatch.delenv("VORTEX_URL", raising=False)
    assert models_mod.is_router_configured() is False

    monkeypatch.setenv("VORTEX_URL", "http://localhost:9000")
    assert models_mod.is_router_configured() is True

    monkeypatch.setenv("VORTEX_URL", "")
    assert models_mod.is_router_configured() is False


def test_router_models_deduplicated(monkeypatch, httpserver):
    _serve_router_models(
        httpserver, [models_mod.ROUTER_MODEL_ID, models_mod.ROUTER_MODEL_ID]
    )
    monkeypatch.setenv("VORTEX_URL", _router_base(httpserver))

    assert models_mod.router_models() == [
        {"id": models_mod.ROUTER_MODEL_ID, "source": "router"}
    ]


def test_router_chat_endpoint_uses_vortex_url(monkeypatch):
    monkeypatch.setenv("VORTEX_URL", "http://127.0.0.1:7777")

    assert models_mod.router_chat_endpoint() == (
        "http://127.0.0.1:7777/v1/chat/completions"
    )


# --- list_models() / list_model_catalog() ------------------------------------


def test_router_models_included_in_list_models(monkeypatch, httpserver):
    _serve_router_models(httpserver, [models_mod.ROUTER_MODEL_ID])
    monkeypatch.setenv("VORTEX_URL", _router_base(httpserver))
    monkeypatch.setattr(
        models_mod, "is_script_model_loaded", lambda model_id: False
    )

    result = models_mod.list_models()

    assert {"id": models_mod.ROUTER_MODEL_ID, "source": "router"} in result


def test_get_models_includes_router_when_ready(client, monkeypatch, httpserver):
    _serve_router_models(httpserver, [models_mod.ROUTER_MODEL_ID])
    monkeypatch.setenv("VORTEX_URL", _router_base(httpserver))

    resp = client.get("/api/v1/models")

    assert resp.status_code == 200
    entries = {(m["id"], m["source"]) for m in resp.json()["models"]}
    assert (models_mod.ROUTER_MODEL_ID, "router") in entries


def test_router_model_never_in_catalog(client, monkeypatch, httpserver):
    _serve_router_models(httpserver, [models_mod.ROUTER_MODEL_ID])
    monkeypatch.setenv("VORTEX_URL", _router_base(httpserver))

    resp = client.get("/api/v1/models/catalog")

    assert resp.status_code == 200
    entries = {(m["id"], m["source"]) for m in resp.json()["models"]}
    assert (models_mod.ROUTER_MODEL_ID, "router") not in entries


# --- chat routing ------------------------------------------------------------


def test_chat_routes_router_model_to_router_endpoint_and_passes_model(
    client, monkeypatch, httpserver
):
    _serve_router_models(httpserver, [models_mod.ROUTER_MODEL_ID])
    monkeypatch.setenv("VORTEX_URL", _router_base(httpserver))
    captured = {}
    _patch_stream_reply(monkeypatch, captured)

    resp = client.post(
        "/api/v1/chat",
        json={"message": "hello", "model": models_mod.ROUTER_MODEL_ID},
    )

    assert resp.status_code == 200
    assert captured["endpoint_override"] == (
        _router_base(httpserver) + "/v1/chat/completions"
    )
    assert captured["model"] == models_mod.ROUTER_MODEL_ID


def test_chat_router_model_not_listed_is_422(client, monkeypatch, httpserver):
    _serve_router_models(httpserver, ["other-model"])
    monkeypatch.setenv("VORTEX_URL", _router_base(httpserver))

    resp = client.post(
        "/api/v1/chat",
        json={"message": "hello", "model": models_mod.ROUTER_MODEL_ID},
    )

    assert resp.status_code == 422


def test_chat_router_model_router_down_is_422(client, monkeypatch):
    # Simulate the router being unreachable without touching the
    # session-shared httpserver (stopping it breaks every later
    # httpserver-based test when the suite runs as sorted node-ids).
    monkeypatch.setenv("VORTEX_URL", "http://127.0.0.1:1")

    def _raise(*args, **kwargs):
        raise models_mod.httpx.ConnectError("connection refused")

    monkeypatch.setattr(models_mod.httpx, "get", _raise)

    resp = client.post(
        "/api/v1/chat",
        json={"message": "hello", "model": models_mod.ROUTER_MODEL_ID},
    )

    assert resp.status_code == 422


def test_chat_internal_path_untouched_when_vortex_url_unset(
    client, monkeypatch
):
    monkeypatch.delenv("VORTEX_URL", raising=False)
    captured = {}
    _patch_stream_reply(monkeypatch, captured)

    resp = client.post(
        "/api/v1/chat",
        json={"message": "hello", "model": models_mod.ROUTER_MODEL_ID},
    )

    assert resp.status_code == 200
    assert captured["endpoint_override"] is None
    assert captured["model"] == models_mod.ROUTER_MODEL_ID
