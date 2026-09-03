"""
Oracle for spec v115 AC-175..AC-181: the router recut — the full dynamic
ready set through the vortex universal surface. Supersedes the v107
single-model oracle (AC-170..AC-174, retired by ERD-DELTA v115). Observes
ONLY contracts.entry_points (src.main:app, src.services.models module + the
router seams, src.services.llm:stream_reply) and contracts.routes
(POST /api/v1/chat, GET /api/v1/models, GET /api/v1/models/catalog). The
router endpoint is simulated with pytest-httpserver; no live vortex
required.

AC-175: GET /api/v1/models lists every ready router model (full set, probe
        order, deduplicated), each with source "router".
AC-176: probe failure / empty ready set -> no router models in the list;
        router models never in the catalog.
AC-177: chat naming any ready router model streams from
        {VORTEX_URL}/v1/chat/completions with the id passed through.
AC-178: chat naming a model not in the ready set falls through to the local
        path (no pre-stream 422).
AC-179: router-routed chat whose stream errors after the model left the
        ready set surfaces the exact not-ready message with a local
        fallback offer (200 SSE, never a server error).
AC-180: router-routed chat whose stream errors while the model is still
        ready surfaces the generic fallback message.
AC-181: no fixed router model id constant exists (ROUTER_MODEL_ID retired).
"""

import json

import pytest
from fastapi.testclient import TestClient
from werkzeug.wrappers import Response

import src.services.llm as llm_mod
import src.services.models as models_mod
from src.main import app


@pytest.fixture
def client():
    return TestClient(app)


def _router_base(httpserver) -> str:
    """Base URL of the simulated router (no trailing slash)."""
    return httpserver.url_for("/").rstrip("/")


def _serve_router_models(httpserver, ids):
    """Simulate the vortex universal surface's GET /v1/models (ready-only)."""
    httpserver.expect_request("/v1/models").respond_with_json(
        {
            "object": "list",
            "data": [
                {"id": model_id, "object": "model"} for model_id in ids
            ],
        }
    )


def _serve_router_models_stateful(httpserver, id_sets):
    """Simulate a ready set that changes between probes: probe n serves
    id_sets[n-1] (the last set repeats). Models the unload race where the
    model leaves the ready set between listing and send."""
    state = {"calls": 0}

    def handler(request):
        index = min(state["calls"], len(id_sets) - 1)
        state["calls"] += 1
        return Response(
            json.dumps(
                {
                    "object": "list",
                    "data": [
                        {"id": model_id, "object": "model"}
                        for model_id in id_sets[index]
                    ],
                }
            ),
            status=200,
            content_type="application/json",
        )

    httpserver.expect_request("/v1/models").respond_with_handler(handler)


def _patch_stream_reply(monkeypatch, captured, chunks=None):
    def fake_stream_reply(message, history=(), endpoint_override=None, model=None):
        captured["endpoint_override"] = endpoint_override
        captured["model"] = model
        yield from (
            chunks if chunks is not None else [("token", "hi"), ("done",)]
        )

    monkeypatch.setattr(llm_mod, "stream_reply", fake_stream_reply)


def _error_message(resp) -> str:
    """Extract the message of the single SSE error event from a chat reply."""
    events = [
        block
        for block in resp.text.strip().split("\n\n")
        if block.startswith("event: error")
    ]
    assert len(events) == 1, f"expected exactly one error event, got {events!r}"
    data_line = events[0].split("\n", 1)[1]
    assert data_line.startswith("data: ")
    return json.loads(data_line[len("data: "):])["message"]


# --- router_models() — full ready set (AC-175/AC-176) ------------------------


def test_router_models_lists_router_when_router_reports_it(monkeypatch, httpserver):
    _serve_router_models(httpserver, ["m1", "m2"])
    monkeypatch.setenv("VORTEX_URL", _router_base(httpserver))

    assert models_mod.router_models() == [
        {"id": "m1", "source": "router"},
        {"id": "m2", "source": "router"},
    ]


def test_router_models_empty_when_router_omits_it(monkeypatch, httpserver):
    _serve_router_models(httpserver, [])
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


def test_router_models_deduplicated(monkeypatch, httpserver):
    _serve_router_models(httpserver, ["m1", "m1"])
    monkeypatch.setenv("VORTEX_URL", _router_base(httpserver))

    assert models_mod.router_models() == [{"id": "m1", "source": "router"}]


# --- is_router_model() — dynamic membership (AC-177/AC-178) ------------------


def test_is_router_model_true_for_any_ready_id(monkeypatch, httpserver):
    _serve_router_models(httpserver, ["m1", "m2"])
    monkeypatch.setenv("VORTEX_URL", _router_base(httpserver))

    assert models_mod.is_router_model("m1") is True
    assert models_mod.is_router_model("m2") is True


def test_is_router_model_false_when_not_listed_or_down(monkeypatch, httpserver):
    _serve_router_models(httpserver, ["m1"])
    monkeypatch.setenv("VORTEX_URL", _router_base(httpserver))

    assert models_mod.is_router_model("m2") is False

    monkeypatch.setenv("VORTEX_URL", "http://127.0.0.1:1")

    def _raise(*args, **kwargs):
        raise models_mod.httpx.ConnectError("connection refused")

    monkeypatch.setattr(models_mod.httpx, "get", _raise)

    assert models_mod.is_router_model("m1") is False


# --- config / endpoint seams (unchanged by the recut) -------------------------


def test_is_router_configured_reflects_env(monkeypatch):
    monkeypatch.delenv("VORTEX_URL", raising=False)
    assert models_mod.is_router_configured() is False

    monkeypatch.setenv("VORTEX_URL", "http://localhost:9000")
    assert models_mod.is_router_configured() is True

    monkeypatch.setenv("VORTEX_URL", "")
    assert models_mod.is_router_configured() is False


def test_router_chat_endpoint_uses_vortex_url(monkeypatch):
    monkeypatch.setenv("VORTEX_URL", "http://127.0.0.1:7777")

    assert models_mod.router_chat_endpoint() == (
        "http://127.0.0.1:7777/v1/chat/completions"
    )


# --- list_models() / list_model_catalog() (AC-175/AC-176) --------------------


def test_router_models_included_in_list_models(monkeypatch, httpserver):
    _serve_router_models(httpserver, ["m1", "m2"])
    monkeypatch.setenv("VORTEX_URL", _router_base(httpserver))
    monkeypatch.setattr(
        models_mod, "is_script_model_loaded", lambda model_id: False
    )

    result = models_mod.list_models()

    assert {"id": "m1", "source": "router"} in result
    assert {"id": "m2", "source": "router"} in result


def test_get_models_includes_router_when_ready(client, monkeypatch, httpserver):
    _serve_router_models(httpserver, ["m1", "m2"])
    monkeypatch.setenv("VORTEX_URL", _router_base(httpserver))

    resp = client.get("/api/v1/models")

    assert resp.status_code == 200
    entries = {(m["id"], m["source"]) for m in resp.json()["models"]}
    assert ("m1", "router") in entries
    assert ("m2", "router") in entries


def test_router_model_never_in_catalog(client, monkeypatch, httpserver):
    _serve_router_models(httpserver, ["m1"])
    monkeypatch.setenv("VORTEX_URL", _router_base(httpserver))

    resp = client.get("/api/v1/models/catalog")

    assert resp.status_code == 200
    entries = {(m["id"], m["source"]) for m in resp.json()["models"]}
    assert ("m1", "router") not in entries


# --- ROUTER_MODEL_ID retirement (AC-181) --------------------------------------


def test_router_model_id_constant_retired():
    assert not hasattr(models_mod, "ROUTER_MODEL_ID")


# --- chat routing (AC-177/AC-178) ---------------------------------------------


def test_chat_routes_router_model_to_router_endpoint_and_passes_model(
    client, monkeypatch, httpserver
):
    _serve_router_models(httpserver, ["m1", "m2"])
    monkeypatch.setenv("VORTEX_URL", _router_base(httpserver))
    captured = {}
    _patch_stream_reply(monkeypatch, captured)

    resp = client.post(
        "/api/v1/chat",
        json={"message": "hello", "model": "m2"},
    )

    assert resp.status_code == 200
    assert captured["endpoint_override"] == (
        _router_base(httpserver) + "/v1/chat/completions"
    )
    assert captured["model"] == "m2"


def test_chat_router_model_not_listed_falls_through_to_local_path(
    client, monkeypatch, httpserver
):
    _serve_router_models(httpserver, ["other-model"])
    monkeypatch.setenv("VORTEX_URL", _router_base(httpserver))
    captured = {}
    _patch_stream_reply(monkeypatch, captured)

    resp = client.post(
        "/api/v1/chat",
        json={"message": "hello", "model": "m1"},
    )

    assert resp.status_code == 200
    assert captured["endpoint_override"] is None
    assert captured["model"] == "m1"


def test_chat_router_model_router_down_falls_through_to_local_path(
    client, monkeypatch
):
    # Simulate the router being unreachable without touching the
    # session-shared httpserver (stopping it breaks every later
    # httpserver-based test when the suite runs as sorted node-ids).
    monkeypatch.setenv("VORTEX_URL", "http://127.0.0.1:1")

    def _raise(*args, **kwargs):
        raise models_mod.httpx.ConnectError("connection refused")

    monkeypatch.setattr(models_mod.httpx, "get", _raise)
    captured = {}
    _patch_stream_reply(monkeypatch, captured)

    resp = client.post(
        "/api/v1/chat",
        json={"message": "hello", "model": "m1"},
    )

    assert resp.status_code == 200
    assert captured["endpoint_override"] is None
    assert captured["model"] == "m1"


def test_chat_internal_path_untouched_when_vortex_url_unset(
    client, monkeypatch
):
    monkeypatch.delenv("VORTEX_URL", raising=False)
    captured = {}
    _patch_stream_reply(monkeypatch, captured)

    resp = client.post(
        "/api/v1/chat",
        json={"message": "hello", "model": "m1"},
    )

    assert resp.status_code == 200
    assert captured["endpoint_override"] is None
    assert captured["model"] == "m1"


# --- 404 race: the model leaves the ready set between listing and send --------


def test_chat_router_404_race_surfaces_not_ready_message(
    client, monkeypatch, httpserver
):
    # Probe 1 (the routing decision) sees m1 ready; probe 2 (the re-probe
    # when the stream errors) sees it gone — the unload race. Per AC-182 the
    # user sees the single generic retry line, with no model-switch suggestion
    # (AC-179's model-specific "pick a local model" notice is superseded).
    _serve_router_models_stateful(httpserver, [["m1"], []])
    monkeypatch.setenv("VORTEX_URL", _router_base(httpserver))
    captured = {}
    _patch_stream_reply(monkeypatch, captured, chunks=[("error",)])

    resp = client.post(
        "/api/v1/chat",
        json={"message": "hello", "model": "m1"},
    )

    assert resp.status_code == 200
    assert captured["endpoint_override"] == (
        _router_base(httpserver) + "/v1/chat/completions"
    )
    assert _error_message(resp) == llm_mod.FALLBACK_REPLY


def test_chat_router_error_while_still_ready_is_generic(
    client, monkeypatch, httpserver
):
    _serve_router_models(httpserver, ["m1"])
    monkeypatch.setenv("VORTEX_URL", _router_base(httpserver))
    captured = {}
    _patch_stream_reply(monkeypatch, captured, chunks=[("error",)])

    resp = client.post(
        "/api/v1/chat",
        json={"message": "hello", "model": "m1"},
    )

    assert resp.status_code == 200
    assert _error_message(resp) == llm_mod.FALLBACK_REPLY
