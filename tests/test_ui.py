"""Frozen UI suite (D-58) — AC-27..AC-33, browser oracle for the frontend.

Element location: contracts.ui testids ONLY (enforced by
check-test-surface.py at freeze). Synchronization: Playwright auto-waiting
via expect() ONLY (refreeze rejects sleeps/timeout waits). Zero retries —
if one of these flakes, the spec is wrong, not the run.
"""
import re

from playwright.sync_api import Page, expect


def _send(page: Page, text: str) -> None:
    page.get_by_test_id("message-input").fill(text)
    page.get_by_test_id("send-btn").click()


def _await_reply(page: Page, count: int = 1) -> None:
    replies = page.get_by_test_id("msg-assistant")
    expect(replies).to_have_count(count)
    expect(replies.nth(count - 1)).to_contain_text("Hello there")


# AC-27 [retrofits M5 think-streaming, broke in M6]
def test_think_toggle_reveals_and_hides_thinking(page: Page, app_url: str) -> None:
    page.goto(app_url)
    _send(page, "hi")
    _await_reply(page)
    think = page.get_by_test_id("think-content").filter(has_text="pondering deeply")
    expect(think.first).to_be_hidden()
    page.get_by_test_id("think-toggle").click()
    expect(think.first).to_be_visible()
    page.get_by_test_id("think-toggle").click()
    expect(think.first).to_be_hidden()


# AC-28 [retrofits AC-23, broke in M6]
def test_model_lock_is_per_thread(page: Page, app_url: str) -> None:
    page.goto(app_url)
    select = page.get_by_test_id("model-select")
    expect(select).to_have_value("alpha-model")
    _send(page, "lock me")
    expect(select).to_be_disabled()
    _await_reply(page)
    page.get_by_test_id("new-thread-btn").click()
    expect(select).to_be_enabled()
    page.get_by_test_id("thread-item").nth(1).click()
    expect(select).to_be_disabled()


# AC-29 [retrofits AC-20/AC-22]
def test_thread_switch_restores_history(page: Page, app_url: str) -> None:
    page.goto(app_url)
    _send(page, "first thread message")
    _await_reply(page)
    page.get_by_test_id("new-thread-btn").click()
    expect(page.get_by_test_id("msg-user")).to_have_count(0)
    _send(page, "second thread message")
    _await_reply(page)
    page.get_by_test_id("thread-item").nth(1).click()
    users = page.get_by_test_id("msg-user")
    expect(users).to_have_count(1)
    expect(users.first).to_contain_text("first thread message")


# AC-30 [new — history hygiene fix]
def test_history_sent_to_backend_has_no_think_markup(
    page: Page, app_url: str, last_chat_request
) -> None:
    page.goto(app_url)
    _send(page, "one")
    _await_reply(page, 1)
    _send(page, "two")
    _await_reply(page, 2)
    req = last_chat_request()
    roles = [m["role"] for m in req["messages"]]
    assert "assistant" in roles, "second request must carry assistant history"
    for m in req["messages"]:
        assert "<think>" not in m["content"], (
            f"history {m['role']} entry leaks think markup: {m['content']!r}"
        )


# AC-31 [new — selection-stability fix]
def test_model_selection_survives_models_refresh(page: Page, app_url: str) -> None:
    page.route(
        "**/api/v1/models/catalog",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"models":[{"id":"nemotron","source":"nemotron","loaded":true}]}',
        ),
    )
    page.route(
        "**/api/v1/script-models/nemotron/unload",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"status":"unloaded","message":null}',
        ),
    )
    page.goto(app_url)
    select = page.get_by_test_id("model-select")
    expect(select).to_have_value("alpha-model")
    stamp = re.search(r"refresh-(\d+)", select.inner_text())
    assert stamp, "stub stamps every models response with refresh-N"
    n = int(stamp.group(1))
    select.select_option("beta-model")
    page.get_by_test_id("eject-model-btn").click()
    page.get_by_test_id("unload-confirm").click()
    expect(select).to_contain_text(f"refresh-{n + 1}")
    expect(select).to_have_value("beta-model")


# AC-32 [retrofits AC-19]
def test_new_chat_creates_unlocked_empty_thread(page: Page, app_url: str) -> None:
    page.goto(app_url)
    items = page.get_by_test_id("thread-item")
    expect(items).to_have_count(1)
    _send(page, "hello")
    _await_reply(page)
    page.get_by_test_id("new-thread-btn").click()
    expect(items).to_have_count(2)
    expect(page.get_by_test_id("msg-user")).to_have_count(0)
    expect(page.get_by_test_id("model-select")).to_be_enabled()


# AC-33 [retrofits AC-21]
def test_thread_title_set_from_first_message(page: Page, app_url: str) -> None:
    page.goto(app_url)
    expect(page.get_by_test_id("thread-item").first).to_contain_text("New Chat")
    _send(page, "The quick brown fox jumps over the lazy dog")
    expect(page.get_by_test_id("thread-item").first).to_contain_text("The quick brown fox")


# AC-34 [M8 — replaces AC-25: refresh now RESTORES]
def test_threads_survive_reload(page: Page, app_url: str) -> None:
    page.goto(app_url)
    _send(page, "persist me please")
    _await_reply(page)
    page.reload()
    items = page.get_by_test_id("thread-item")
    expect(items).to_have_count(1)
    expect(items.first).to_contain_text("persist me please")
    users = page.get_by_test_id("msg-user")
    expect(users).to_have_count(1)
    expect(users.first).to_contain_text("persist me please")
    expect(page.get_by_test_id("msg-assistant").first).to_contain_text("Hello there")
    expect(page.get_by_test_id("model-select")).to_be_disabled()


# AC-41 [M9 — failed reply retains the user's message]
def test_failed_reply_keeps_user_message(page: Page, app_url: str) -> None:
    page.goto(app_url)
    # Route the chat request to an aborted response so the stream fails.
    page.route("**/api/v1/chat", lambda route: route.abort())
    _send(page, "this must not vanish")
    # user's message stays visible in the thread
    users = page.get_by_test_id("msg-user")
    expect(users).to_have_count(1)
    expect(users.first).to_contain_text("this must not vanish")
    # and it survives a thread switch (i.e. it entered stored history)
    page.get_by_test_id("new-thread-btn").click()
    page.get_by_test_id("thread-item").nth(1).click()
    expect(page.get_by_test_id("msg-user")).to_have_count(1)
    expect(page.get_by_test_id("msg-user").first).to_contain_text("this must not vanish")


# AC-42 [M9 — "thinking..." placeholder before visible answer text]
# Recut M28d: gated stub replaces the wall-clock hold window.
def test_thinking_placeholder_shows_then_clears(page: Page, app_url: str, llm_stub: str) -> None:
    page.goto(app_url)
    _send(page, "SLOWPING please think first")
    reply = page.get_by_test_id("msg-assistant").last
    expect(reply).to_contain_text("thinking...")
    page.request.get(f"{llm_stub}/release-slowping")
    expect(reply).to_contain_text("Hello there")
    expect(reply).not_to_contain_text("thinking...")


# AC-44 [M10 ratify — markdown rendering]
def test_markdown_renders_readably(page: Page, app_url: str) -> None:
    page.goto(app_url)
    _send(page, "format something")
    _await_reply(page)
    bubble = page.get_by_test_id("msg-assistant").last
    expect(bubble).to_contain_text("bold move")
    expect(bubble).not_to_contain_text("**bold move**")
    expect(bubble).to_contain_text("mono bit")
    expect(bubble).not_to_contain_text("`mono bit`")


# AC-45 [M10 ratify — theme switch + persistence]
def test_theme_switch_persists_across_reload(page: Page, app_url: str) -> None:
    page.goto(app_url)
    before = page.evaluate("document.documentElement.getAttribute('data-theme')")
    page.get_by_test_id("theme-toggle").click()
    after = page.evaluate("document.documentElement.getAttribute('data-theme')")
    assert after != before, "toggle must switch the theme"
    page.reload()
    restored = page.evaluate("document.documentElement.getAttribute('data-theme')")
    assert restored == after, "reload must restore the selected theme"


# AC-46 [M10 ratify — thread rename]
def test_thread_rename_via_sidebar_control(page: Page, app_url: str) -> None:
    page.goto(app_url)
    item = page.get_by_test_id("thread-item").first
    item.hover()
    page.get_by_test_id("thread-rename-btn").first.click()
    box = page.get_by_test_id("thread-rename-input")
    box.fill("Renamed by test")
    box.press("Enter")
    expect(page.get_by_test_id("thread-item").first).to_contain_text("Renamed by test")
    page.reload()
    expect(page.get_by_test_id("thread-item").first).to_contain_text("Renamed by test")


# AC-47 [M10 ratify — thread delete via themed modal]
# Recut M28d: native dialog replaced by delete-confirm-modal.
def test_thread_delete_removes_thread(page: Page, app_url: str) -> None:
    page.goto(app_url)
    _send(page, "first thread message")
    _await_reply(page)
    page.get_by_test_id("new-thread-btn").click()
    items = page.get_by_test_id("thread-item")
    expect(items).to_have_count(2)
    items.first.hover()
    page.get_by_test_id("thread-delete-btn").first.click()
    page.get_by_test_id("delete-confirm").click()
    expect(page.get_by_test_id("thread-item")).to_have_count(1)
    page.reload()
    expect(page.get_by_test_id("thread-item")).to_have_count(1)


# AC-48 [M10 ratify — stop button keeps the partial reply]
def test_stop_button_keeps_partial_reply(page: Page, app_url: str) -> None:
    page.goto(app_url)
    select = page.get_by_test_id("model-select")
    expect(select).to_have_value("alpha-model")
    select.select_option("slow-model")
    _send(page, "stream slowly")
    send = page.get_by_test_id("send-btn")
    expect(send).to_have_text("Stop")
    expect(page.get_by_test_id("msg-assistant").last).to_contain_text("tick0")
    send.click()
    expect(send).to_have_text("Send")
    expect(send).to_be_enabled()
    expect(page.get_by_test_id("msg-assistant").last).to_contain_text("tick0")


# AC-49 [M10 ratify — saved system prompt reaches every request]
def test_saved_system_prompt_reaches_requests(
    page: Page, app_url: str, last_chat_request
) -> None:
    page.goto(app_url)
    page.get_by_test_id("settings-toggle").click()
    box = page.get_by_test_id("system-prompt-input")
    box.fill("You are a test harness. Be terse.")
    page.get_by_test_id("settings-save").click()
    _send(page, "obey the prompt")
    _await_reply(page)
    req = last_chat_request()
    first = req["messages"][0]
    assert first["role"] == "system"
    assert first["content"] == "You are a test harness. Be terse."


# AC-53/AC-55 [M12 ratify — the cycle holds all ten themes, wraps at ten]
def test_theme_cycle_reaches_phosphor_and_wraps(page: Page, app_url: str) -> None:
    page.goto(app_url)
    start = page.evaluate("document.documentElement.getAttribute('data-theme')")
    seen = []
    for _ in range(10):
        page.get_by_test_id("theme-toggle").click()
        seen.append(page.evaluate("document.documentElement.getAttribute('data-theme')"))
    assert "phosphor" in seen, f"cycle never reached phosphor: {seen}"
    assert "midnight" in seen, f"cycle never reached midnight: {seen}"
    assert seen[-1] == start, f"ten clicks must wrap to the start: {start} -> {seen}"


# AC-54 [M14 ratify — rain backdrop only while matrix is active]
def test_rain_backdrop_only_in_matrix(page: Page, app_url: str) -> None:
    page.goto(app_url)
    for _ in range(4):
        if page.evaluate("document.documentElement.getAttribute('data-theme')") == "matrix":
            break
        page.get_by_test_id("theme-toggle").click()
    assert page.evaluate("document.documentElement.getAttribute('data-theme')") == "matrix"
    expect(page.get_by_test_id("matrix-rain")).to_be_visible()
    page.get_by_test_id("theme-toggle").click()
    expect(page.get_by_test_id("matrix-rain")).to_be_hidden()


# AC-56/AC-57 [M15 — terminal title bar only while phosphor is active]
def test_terminal_titlebar_only_in_phosphor(page: Page, app_url: str) -> None:
    page.goto(app_url)
    for _ in range(4):
        if page.evaluate("document.documentElement.getAttribute('data-theme')") == "phosphor":
            break
        page.get_by_test_id("theme-toggle").click()
    assert page.evaluate("document.documentElement.getAttribute('data-theme')") == "phosphor"
    expect(page.get_by_test_id("terminal-titlebar")).to_be_visible()
    page.get_by_test_id("theme-toggle").click()
    expect(page.get_by_test_id("terminal-titlebar")).to_be_hidden()


# AC-59 [M16 — newest thread on top]
def test_sidebar_lists_newest_thread_first(page: Page, app_url: str) -> None:
    page.goto(app_url)
    _send(page, "older thread anchor")
    _await_reply(page)
    page.get_by_test_id("new-thread-btn").click()
    _send(page, "newer thread anchor")
    _await_reply(page)
    items = page.get_by_test_id("thread-item")
    expect(items).to_have_count(2)
    expect(items.nth(0)).to_contain_text("newer thread anchor")
    expect(items.nth(1)).to_contain_text("older thread anchor")


# AC-63/AC-64/AC-65 [M18 — sidebar search filters the thread list]
def test_sidebar_search_filters_threads(page: Page, app_url: str) -> None:
    page.goto(app_url)
    _send(page, "koala first thread anchor")
    _await_reply(page)
    page.get_by_test_id("new-thread-btn").click()
    _send(page, "zebra second thread anchor")
    _await_reply(page)
    items = page.get_by_test_id("thread-item")
    expect(items).to_have_count(2)
    box = page.get_by_test_id("thread-search-input")
    box.fill("koala")
    expect(items).to_have_count(1)
    expect(items.first).to_contain_text("koala first thread")
    box.fill("")
    expect(items).to_have_count(2)
    expect(items.nth(0)).to_contain_text("zebra second thread")


# AC-66/AC-67 [M19 — search hits highlighted inside the opened thread]
def test_search_hits_highlighted_in_open_thread(page: Page, app_url: str) -> None:
    page.goto(app_url)
    _send(page, "wombat hidden anchor message")
    _await_reply(page)
    box = page.get_by_test_id("thread-search-input")
    box.fill("wombat")
    items = page.get_by_test_id("thread-item")
    expect(items).to_have_count(1)
    items.first.click()
    hits = page.get_by_test_id("search-hit")
    expect(hits.first).to_be_visible()
    expect(hits.first).to_contain_text("wombat")
    box.fill("")
    expect(page.get_by_test_id("search-hit")).to_have_count(0)


# AC-69/AC-70/AC-71 [M20 — search-hit counter and prev/next cycling]
def test_search_hit_count_and_navigation(page: Page, app_url: str) -> None:
    page.goto(app_url)
    _send(page, "quokka alpha then quokka beta then quokka gamma")
    _await_reply(page)
    page.get_by_test_id("thread-search-input").fill("quokka")
    items = page.get_by_test_id("thread-item")
    expect(items).to_have_count(1)
    items.first.click()
    counter = page.get_by_test_id("search-hit-count")
    expect(counter).to_be_visible()
    expect(counter).to_have_text("1/3")
    page.get_by_test_id("search-next-btn").click()
    expect(counter).to_have_text("2/3")
    page.get_by_test_id("search-next-btn").click()
    page.get_by_test_id("search-next-btn").click()
    expect(counter).to_have_text("1/3")
    page.get_by_test_id("search-prev-btn").click()
    expect(counter).to_have_text("3/3")
    page.get_by_test_id("thread-search-input").fill("")
    expect(counter).to_be_hidden()


# AC-75/AC-76 [M23 — persist failures are visible, recovery clears]
def test_save_failure_indicator_shows_then_clears(page: Page, app_url: str) -> None:
    page.goto(app_url)
    page.route(
        "**/api/v1/threads",
        lambda route: route.fulfill(status=500, body="{}")
        if route.request.method == "PUT"
        else route.fallback(),
    )
    _send(page, "message while saves are broken")
    _await_reply(page)
    indicator = page.get_by_test_id("save-status")
    expect(indicator).to_contain_text("not saved")     # AC-75
    page.unroute("**/api/v1/threads")
    _send(page, "message after saves recover")
    _await_reply(page, count=2)  # same thread: two replies now
    expect(indicator).to_have_text("")                 # AC-76


# AC-80 [M24 — unreadable history is announced, with its backup noted]
def test_history_quarantine_indicator_shows(page: Page, app_url: str, app_data_path) -> None:
    app_data_path.write_text("{not valid json!!")
    page.goto(app_url)
    expect(page.get_by_test_id("history-status")).to_have_text(
        "history unreadable (backup kept)"
    )


# AC-81 [M24 — healthy loads say nothing]
def test_history_status_empty_when_healthy(page: Page, app_url: str) -> None:
    page.goto(app_url)
    expect(page.get_by_test_id("history-status")).to_have_text("")


# AC-83 [M24 — ratifies the 2026-07-15 hover-timestamp live-fix: past-day
# messages carry their calendar date, not a bare time]
def test_bubble_meta_includes_date_for_past_messages(page: Page, app_url: str) -> None:
    from datetime import datetime, timedelta

    past = datetime.now() - timedelta(days=3)
    expected_time = past.strftime("%H:%M")
    payload = {"threads": [{
        "id": 1, "title": "Old chat", "model": "", "locked": False,
        "messages": [{"role": "user", "content": "from another day",
                      "ts": int(past.timestamp()), "model": ""}],
    }]}
    page.request.put(app_url + "/api/v1/threads", data=payload)
    page.goto(app_url)
    meta = page.get_by_test_id("msg-meta").first
    # date ahead of the time — never a bare HH:MM for a past-day message.
    # (locale-agnostic: asserts a non-empty date prefix, not its wording)
    expect(meta).to_have_attribute(
        "data-meta", re.compile(rf"^\S.+ {expected_time}$")
    )
