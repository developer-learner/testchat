"""M34 browser oracle: the new registry entry uses the carried generic UI."""

from playwright.sync_api import Page, expect


MODEL_ID = "deepseek-v4-flash-0731"


def test_deepseek_0731_option_uses_generic_confirmation(
    page: Page, app_url: str
) -> None:
    load_requests = []

    page.route(
        "**/api/v1/models",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"models":[]}',
        ),
    )
    page.route(
        "**/api/v1/models/catalog",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=(
                '{"models":[{"id":"deepseek-v4-flash-0731",'
                '"source":"deepseek-v4-flash-0731","loaded":false}]}'
            ),
        ),
    )
    page.route(
        "**/api/v1/status",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=(
                '{"nemotron_loaded":false,"nemotron_rss_gb":0,'
                '"ram_used_gb":1,"ram_total_gb":64,"loadable_gb":63,'
                '"web_configured":false}'
            ),
        ),
    )

    def fulfill_load(route) -> None:
        load_requests.append(route.request)
        route.fulfill(
            status=200,
            content_type="application/json",
            body='{"status":"loaded"}',
        )

    page.route(
        "**/api/v1/script-models/deepseek-v4-flash-0731/load",
        fulfill_load,
    )

    page.goto(app_url)
    select = page.get_by_test_id("model-select")
    expect(select).to_contain_text(MODEL_ID)
    option_label = select.evaluate(
        "(el, id) => Array.from(el.options).find(o => o.value === id)?.textContent",
        MODEL_ID,
    )
    assert option_label.endswith(MODEL_ID)
    assert option_label != MODEL_ID, "carried loaded/unloaded prefix is missing"

    select.select_option(MODEL_ID)
    modal = page.get_by_test_id("load-confirm-modal")
    expect(modal).to_be_visible()
    expect(modal).to_contain_text(MODEL_ID)

    with page.expect_request(
        "**/api/v1/script-models/deepseek-v4-flash-0731/load"
    ) as request_info:
        page.get_by_test_id("load-confirm").click()

    assert request_info.value.method == "POST"
    expect(modal).to_be_hidden()
    assert len(load_requests) == 1
