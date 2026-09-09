"""
Frozen oracle for the Vortex cutover (T9, spec v123). CEO-approved design:
tasks/T9-cutover-design.md (2026-09-01). Vortex is the primary model source,
the picker is ready-only and grouped, model management lives in Vortex (a
"Manage in Vortex" link), the active model's source is shown, and the local
path stays as a labelled fallback when Vortex is unreachable.

Backend tests observe only contracts.entry_points (src.main:app,
src.services.models:router_status) and contracts.routes (GET /api/v1/models);
the router is simulated with pytest-httpserver, no live Vortex. UI tests
observe only contracts.ui testids (model-select, manage-in-vortex,
active-model-source); the models response is simulated with page.route.

AC-183: GET /api/v1/models carries a router {configured, reachable} object.
AC-184: ready-only grouped picker (Vortex primary / Local fallback optgroups).
AC-185: a manage-in-vortex link targets the Vortex dashboard, new tab.
AC-186: router unreachable -> Vortex group + manage link disabled, local stays.
AC-187: active-model-source reads "via Vortex" / "via local".
AC-188 (supersedes AC-31/AC-132/AC-167): no local lifecycle controls; a ready
        pick opens no load confirmation.
"""

import json

import pytest
from fastapi.testclient import TestClient
from playwright.sync_api import Page, expect

import src.services.models as models_mod
from src.main import app


@pytest.fixture
def client():
    return TestClient(app)


def _router_base(httpserver) -> str:
    return httpserver.url_for("/").rstrip("/")


def _serve_router_models(httpserver, ids) -> None:
    httpserver.expect_request("/v1/models").respond_with_json(
        {"object": "list", "data": [{"id": i, "object": "model"} for i in ids]}
    )


# --- AC-183: backend router status --------------------------------------------


def test_router_status_reflects_configured_and_reachable(monkeypatch, httpserver):
    monkeypatch.delenv("VORTEX_URL", raising=False)
    assert models_mod.router_status() == {"configured": False, "reachable": False}

    _serve_router_models(httpserver, ["m1"])
    monkeypatch.setenv("VORTEX_URL", _router_base(httpserver))
    assert models_mod.router_status() == {"configured": True, "reachable": True}

    monkeypatch.setenv("VORTEX_URL", "http://127.0.0.1:1")

    def _raise(*args, **kwargs):
        raise models_mod.httpx.ConnectError("connection refused")

    monkeypatch.setattr(models_mod.httpx, "get", _raise)
    assert models_mod.router_status() == {"configured": True, "reachable": False}


def test_get_models_includes_router_object(client, monkeypatch):
    monkeypatch.delenv("VORTEX_URL", raising=False)
    resp = client.get("/api/v1/models")
    assert resp.status_code == 200
    body = resp.json()
    assert "router" in body, body
    assert set(body["router"].keys()) == {"configured", "reachable"}
    assert body["router"]["configured"] is False
    assert isinstance(body["router"]["reachable"], bool)


# --- UI: grouped picker, manage link, fallback, source indicator --------------

_READY_BOTH = {
    "models": [
        {"id": "qwen-vortex", "source": "router"},
        {"id": "local-a", "source": "lmstudio"},
    ],
    "router": {"configured": True, "reachable": True},
}

_GROUPS_JS = (
    "[...document.querySelector('[data-testid=\"model-select\"]')"
    ".querySelectorAll('optgroup')].map(g => ({label: g.label, "
    "disabled: g.disabled, opts: [...g.querySelectorAll('option')]"
    ".map(o => o.value)}))"
)


def _route_models(page, payload) -> None:
    page.route(
        "**/api/v1/models",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(payload),
        ),
    )


def test_picker_is_ready_only_and_grouped(page: Page, app_url: str) -> None:
    _route_models(page, _READY_BOTH)
    page.goto(app_url)
    select = page.get_by_test_id("model-select")
    expect(select).to_contain_text("qwen-vortex")
    expect(select).to_contain_text("local-a")
    groups = page.evaluate(_GROUPS_JS)
    vortex = next((g for g in groups if "Vortex" in g["label"]), None)
    local = next((g for g in groups if "Local" in g["label"]), None)
    assert vortex is not None and local is not None, groups
    assert "qwen-vortex" in vortex["opts"], groups
    assert "local-a" in local["opts"], groups


def test_manage_in_vortex_link_targets_router(page: Page, app_url: str) -> None:
    _route_models(page, _READY_BOTH)
    page.goto(app_url)
    link = page.get_by_test_id("manage-in-vortex")
    expect(link).to_have_attribute("href", "http://127.0.0.1:9000/")
    expect(link).to_have_attribute("target", "_blank")


def test_vortex_group_and_manage_disabled_when_unreachable(
    page: Page, app_url: str
) -> None:
    payload = {
        "models": _READY_BOTH["models"],
        "router": {"configured": True, "reachable": False},
    }
    _route_models(page, payload)
    page.goto(app_url)
    expect(page.get_by_test_id("manage-in-vortex")).to_have_attribute(
        "aria-disabled", "true"
    )
    groups = page.evaluate(_GROUPS_JS)
    vortex = next((g for g in groups if "Vortex" in g["label"]), None)
    assert vortex is not None and vortex["disabled"] is True, groups
    # The local fallback stays selectable.
    select = page.get_by_test_id("model-select")
    select.select_option("local-a")
    expect(select).to_have_value("local-a")


def test_active_model_source_indicator(page: Page, app_url: str) -> None:
    _route_models(page, _READY_BOTH)
    page.goto(app_url)
    select = page.get_by_test_id("model-select")
    select.select_option("qwen-vortex")
    expect(page.get_by_test_id("active-model-source")).to_have_text("via Vortex")
    select.select_option("local-a")
    expect(page.get_by_test_id("active-model-source")).to_have_text("via local")
