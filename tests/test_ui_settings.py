"""
Frozen UI oracle for settings-save failure visibility (spec v100; v101 and
v102 re-freezes restaged this file for task-mapping and brief corrections —
no behavioral change) AC-166: a failed save keeps the dialog open and
reports the failure — a user is never left believing the system prompt was
saved. Browser-only observation (D-58: no time.sleep; the server failure is
simulated with page.route).
"""

from playwright.sync_api import Page, expect


def test_settings_save_failure_keeps_the_modal_open_and_is_visible(
    page: Page, app_url: str
) -> None:
    page.route("**/api/v1/settings", lambda route: route.fulfill(status=500, body="{}"))
    page.goto(app_url)
    page.get_by_test_id("settings-toggle").click()
    page.get_by_test_id("system-prompt-input").fill("you will never see this saved")
    page.get_by_test_id("settings-save").click()

    expect(page.get_by_test_id("settings-status")).to_be_visible()
    expect(page.get_by_test_id("settings-status")).to_contain_text("Save failed")
    expect(page.get_by_test_id("settings-save")).to_be_visible()
