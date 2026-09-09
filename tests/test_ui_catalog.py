"""
Frozen UI oracle for the model dropdown dedup (spec v101; consolidation
freeze pinning the 2ebd2bd direct fix — no app changes in that delta)
AC-167: when the models list and the script-model catalog both name the
same model id, the dropdown renders exactly one option for it, so a loaded
script model is never offered twice. Browser-only observation (D-58: no
time.sleep; both sources are simulated with page.route; option counts are
read through a JS evaluate on the locked model-select testid).

Spec v107 (AC-170/AC-171): a router-sourced model in the models list renders
as one selectable option — the router model's dropdown presence with no UI
change, and no option when the router is absent from the list.
"""

from playwright.sync_api import Page, expect


def test_model_dropdown_shows_each_script_model_once(
    page: Page, app_url: str
) -> None:
    page.route(
        "**/api/v1/models",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"models":[{"type":"llm","key":"nemotron","loaded_instances":[{"identifier":"nemotron"}]}]}',
        ),
    )
    page.route(
        "**/api/v1/models/catalog",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"models":[{"id":"nemotron","source":"nemotron","loaded":true},{"id":"solo-script","source":"other","loaded":true}]}',
        ),
    )
    page.goto(app_url)
    select = page.get_by_test_id("model-select")
    expect(select).to_contain_text("solo-script")
    counts = page.evaluate(
        "[...document.querySelector('[data-testid=\"model-select\"]').options]"
        ".reduce((m, o) => (m[o.value] = (m[o.value] || 0) + 1, m), {})"
    )
    assert counts.get("nemotron") == 1, f"overlap id duplicated: {counts!r}"
    assert counts.get("solo-script") == 1, f"catalog id duplicated: {counts!r}"


def test_model_dropdown_lists_router_model_from_models_list(
    page: Page, app_url: str
) -> None:
    page.route(
        "**/api/v1/models",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"models":[{"id":"qwen3.8-27b-8bit","source":"router"}]}',
        ),
    )
    page.route(
        "**/api/v1/models/catalog",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"models":[]}',
        ),
    )
    page.goto(app_url)
    select = page.get_by_test_id("model-select")
    expect(select).to_contain_text("qwen3.8-27b-8bit")
    counts = page.evaluate(
        "[...document.querySelector('[data-testid=\"model-select\"]').options]"
        ".reduce((m, o) => (m[o.value] = (m[o.value] || 0) + 1, m), {})"
    )
    assert counts.get("qwen3.8-27b-8bit") == 1, (
        f"router id duplicated: {counts!r}"
    )