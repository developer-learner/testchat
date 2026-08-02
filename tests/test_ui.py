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


# AC-28 retired in v67 (M32) — the per-thread model lock is gone;
# AC-133 replaces it with "selector enabled at all times." The former
# canonical test `test_model_lock_is_per_thread` is removed from the
# suite by absence; see M32 section at end of file for AC-133..AC-135.


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


# AC-32 [retrofits AC-19; v67 (M32) dropped the trailing selector-enabled
# assertion — AC-133 covers "selector enabled" universally now]
def test_new_chat_creates_unlocked_empty_thread(page: Page, app_url: str) -> None:
    page.goto(app_url)
    items = page.get_by_test_id("thread-item")
    expect(items).to_have_count(1)
    _send(page, "hello")
    _await_reply(page)
    page.get_by_test_id("new-thread-btn").click()
    expect(items).to_have_count(2)
    expect(page.get_by_test_id("msg-user")).to_have_count(0)


# AC-33 [retrofits AC-21]
def test_thread_title_set_from_first_message(page: Page, app_url: str) -> None:
    page.goto(app_url)
    expect(page.get_by_test_id("thread-item").first).to_contain_text("New Chat")
    _send(page, "The quick brown fox jumps over the lazy dog")
    expect(page.get_by_test_id("thread-item").first).to_contain_text("The quick brown fox")


# AC-34 [M8 — replaces AC-25: refresh RESTORES; v67 (M32) dropped the
# trailing disable-after-reload assertion — AC-28 retired, AC-133 keeps
# the selector enabled]
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
    revision = page.request.get(app_url + "/api/v1/threads").json()["revision"]
    payload = {"revision": revision, "threads": [{
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


# AC-100 [v57 — the thread's model is marked by native selection only: labels
# never carry a "✓" (the OS select renders its own checkmark; a label glyph
# duplicated it — "✓ ✓" on macOS, CEO-rejected 2026-07-19)]
def test_model_option_labels_never_carry_checkmark(page: Page, app_url: str) -> None:
    page.route(
        "**/api/v1/models/catalog",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"models":[{"id":"nemotron","source":"nemotron","loaded":true}]}',
        ),
    )
    page.goto(app_url)
    select = page.get_by_test_id("model-select")
    expect(select).to_have_value("alpha-model")  # options are populated
    expect(select).not_to_contain_text("✓")      # at rest
    _send(page, "bind this thread")
    _await_reply(page)
    expect(select).not_to_contain_text("✓")      # after send: still no label glyph
    # (dropped in v67 (M32): expect(select).to_be_disabled() — AC-28 retired)


# =============================================================================
# M31 (spec v61) — current-chat awareness (AC-111..AC-126)
#
# Header title display, inline rename with full interaction paths, cross-source
# rename parity, sidebar highlight of the current thread, load / refresh
# selection policy, and content safety. See scripts/.approved/PRD.md.
#
# Interaction ACs specified up front (M28 lesson): every cancel path, blur
# behavior, empty-input case, and race with a thread switch is a named test.
# =============================================================================


# AC-111: title visible on load
def test_current_thread_title_shows_in_header(page: Page, app_url: str) -> None:
    page.goto(app_url)
    _send(page, "seed message so the thread gets a real title")
    _await_reply(page)
    sidebar_title = page.get_by_test_id("thread-item").first.inner_text().strip()
    expect(page.get_by_test_id("current-thread-title")).to_have_text(
        re.compile(re.escape(sidebar_title))
    )


# AC-111 / AC-122: title updates on thread switch
def test_header_title_updates_when_switching_threads(page: Page, app_url: str) -> None:
    page.goto(app_url)
    _send(page, "first thread")
    _await_reply(page)
    page.get_by_test_id("new-thread-btn").click()
    _send(page, "second thread")
    _await_reply(page)
    # Switch to the older thread (nth(1) = second in the list, which is
    # the older one because sidebar lists newest first).
    page.get_by_test_id("thread-item").nth(1).click()
    older_sidebar_text = page.get_by_test_id("thread-item").nth(1).inner_text().strip()
    expect(page.get_by_test_id("current-thread-title")).to_have_text(
        re.compile(re.escape(older_sidebar_text))
    )


# AC-112: long titles truncate and expose full text via native tooltip
def test_long_header_title_truncates_with_full_text_in_tooltip(
    page: Page, app_url: str
) -> None:
    page.goto(app_url)
    _send(page, "seed message")
    _await_reply(page)
    long_title = "A" * 200
    page.get_by_test_id("current-thread-title").click()
    box = page.get_by_test_id("current-thread-title-input")
    box.fill(long_title)
    box.press("Enter")
    title = page.get_by_test_id("current-thread-title")
    # Full title reachable via native tooltip regardless of visible truncation.
    expect(title).to_have_attribute("title", long_title)
    # No horizontal reflow: the title element's rendered width must not exceed
    # the header region's available space (asserted as no page-level horizontal
    # scroll being introduced by the long title).
    body_scroll_width = page.evaluate("document.body.scrollWidth")
    body_client_width = page.evaluate("document.body.clientWidth")
    assert body_scroll_width <= body_client_width + 1, (
        "long thread title must not cause horizontal page overflow"
    )


# AC-113: click enters edit mode with input focused and pre-selected
def test_click_header_title_enters_edit_mode(page: Page, app_url: str) -> None:
    page.goto(app_url)
    _send(page, "seed message")
    _await_reply(page)
    page.get_by_test_id("current-thread-title").click()
    box = page.get_by_test_id("current-thread-title-input")
    expect(box).to_be_visible()
    expect(box).to_be_focused()
    # Pre-selected: overwriting with a single character replaces the whole
    # title rather than appending to it.
    box.press("X")
    expect(box).to_have_value("X")


# AC-114: Enter commits header-title edit and persists
def test_enter_commits_header_title_edit(page: Page, app_url: str) -> None:
    page.goto(app_url)
    _send(page, "seed message")
    _await_reply(page)
    page.get_by_test_id("current-thread-title").click()
    box = page.get_by_test_id("current-thread-title-input")
    box.fill("Committed via Enter")
    box.press("Enter")
    expect(page.get_by_test_id("current-thread-title")).to_have_text(
        "Committed via Enter"
    )
    # Persists across reload
    page.reload()
    expect(page.get_by_test_id("current-thread-title")).to_have_text(
        "Committed via Enter"
    )


# AC-115: Escape reverts header-title edit
def test_escape_reverts_header_title_edit(page: Page, app_url: str) -> None:
    page.goto(app_url)
    _send(page, "seed message")
    _await_reply(page)
    prior = page.get_by_test_id("current-thread-title").inner_text()
    page.get_by_test_id("current-thread-title").click()
    box = page.get_by_test_id("current-thread-title-input")
    box.fill("This should be discarded")
    box.press("Escape")
    expect(page.get_by_test_id("current-thread-title")).to_have_text(prior)
    # Persisted title unchanged: reload shows the prior title, not the discard
    page.reload()
    expect(page.get_by_test_id("current-thread-title")).to_have_text(prior)


# AC-117: empty commit reverts to prior title (never persisted as empty)
def test_empty_header_title_commit_reverts_to_prior(
    page: Page, app_url: str
) -> None:
    page.goto(app_url)
    _send(page, "seed message")
    _await_reply(page)
    prior = page.get_by_test_id("current-thread-title").inner_text()
    page.get_by_test_id("current-thread-title").click()
    box = page.get_by_test_id("current-thread-title-input")
    box.fill("   ")   # whitespace-only counts as empty
    box.press("Enter")
    expect(page.get_by_test_id("current-thread-title")).to_have_text(prior)


# AC-118: switching threads mid-edit commits the pending rename first
def test_switching_threads_mid_edit_commits_pending_rename(
    page: Page, app_url: str
) -> None:
    page.goto(app_url)
    _send(page, "first thread")
    _await_reply(page)
    page.get_by_test_id("new-thread-btn").click()
    _send(page, "second thread")
    _await_reply(page)
    # Enter edit mode on the current (newest) thread's title
    page.get_by_test_id("current-thread-title").click()
    page.get_by_test_id("current-thread-title-input").fill("Renamed before switch")
    # Switch to the older thread WITHOUT explicitly committing
    page.get_by_test_id("thread-item").nth(1).click()
    # Return to the previously-edited thread; its title must show the commit
    page.get_by_test_id("thread-item").first.click()
    expect(page.get_by_test_id("current-thread-title")).to_have_text(
        "Renamed before switch"
    )


# AC-119: sidebar rename updates header immediately for the current thread
def test_sidebar_rename_updates_header_immediately(
    page: Page, app_url: str
) -> None:
    page.goto(app_url)
    _send(page, "seed message")
    _await_reply(page)
    item = page.get_by_test_id("thread-item").first
    item.hover()
    page.get_by_test_id("thread-rename-btn").first.click()
    box = page.get_by_test_id("thread-rename-input")
    box.fill("Renamed from sidebar")
    box.press("Enter")
    expect(page.get_by_test_id("current-thread-title")).to_have_text(
        "Renamed from sidebar"
    )


# AC-120: header rename updates sidebar row immediately
def test_header_rename_updates_sidebar_row_immediately(
    page: Page, app_url: str
) -> None:
    page.goto(app_url)
    _send(page, "seed message")
    _await_reply(page)
    page.get_by_test_id("current-thread-title").click()
    box = page.get_by_test_id("current-thread-title-input")
    box.fill("Renamed from header")
    box.press("Enter")
    expect(page.get_by_test_id("thread-item").first).to_contain_text(
        "Renamed from header"
    )


# AC-121: exactly one thread-item is marked data-active="true"
def test_current_thread_is_highlighted_in_sidebar(
    page: Page, app_url: str
) -> None:
    page.goto(app_url)
    _send(page, "first thread")
    _await_reply(page)
    page.get_by_test_id("new-thread-btn").click()
    _send(page, "second thread")
    _await_reply(page)
    items = page.get_by_test_id("thread-item")
    expect(items).to_have_count(2)
    # Current (just-sent) thread is newest — sidebar renders it first
    expect(items.first).to_have_attribute("data-active", "true")
    # And no other thread carries data-active="true"
    active_count = page.locator('[data-testid="thread-item"][data-active="true"]').count()
    assert active_count == 1, f"expected exactly one highlighted thread, got {active_count}"


# AC-122: highlight moves when the user switches threads
def test_highlight_moves_when_switching_threads(
    page: Page, app_url: str
) -> None:
    page.goto(app_url)
    _send(page, "first thread")
    _await_reply(page)
    page.get_by_test_id("new-thread-btn").click()
    _send(page, "second thread")
    _await_reply(page)
    items = page.get_by_test_id("thread-item")
    # Currently second thread is highlighted (it is the newest, first in list)
    expect(items.first).to_have_attribute("data-active", "true")
    # Switch to the older thread
    items.nth(1).click()
    expect(items.nth(1)).to_have_attribute("data-active", "true")
    # And the previously-active one no longer is
    active_count = page.locator('[data-testid="thread-item"][data-active="true"]').count()
    assert active_count == 1


# AC-122: highlight moves to newest-remaining when the current thread is deleted
def test_highlight_moves_when_current_thread_deleted(
    page: Page, app_url: str
) -> None:
    page.goto(app_url)
    _send(page, "keeper thread")
    _await_reply(page)
    page.get_by_test_id("new-thread-btn").click()
    _send(page, "doomed thread")
    _await_reply(page)
    # Newest (doomed) is currently active — delete it
    items = page.get_by_test_id("thread-item")
    items.first.hover()
    page.get_by_test_id("thread-delete-btn").first.click()
    page.get_by_test_id("delete-confirm").click()
    # Only the keeper remains, and it must be the active one
    expect(page.get_by_test_id("thread-item")).to_have_count(1)
    expect(page.get_by_test_id("thread-item").first).to_have_attribute(
        "data-active", "true"
    )
    # Header title reflects the switch
    keeper_title = page.get_by_test_id("thread-item").first.inner_text().strip()
    expect(page.get_by_test_id("current-thread-title")).to_have_text(
        re.compile(re.escape(keeper_title))
    )


# AC-123: reload opens the newest (top-of-sidebar) thread, not a stored pin
def test_reload_opens_newest_thread(page: Page, app_url: str) -> None:
    page.goto(app_url)
    _send(page, "first thread")
    _await_reply(page)
    page.get_by_test_id("new-thread-btn").click()
    _send(page, "second thread")
    _await_reply(page)
    # Deliberately switch AWAY from the newest, so that if the app tried to
    # restore last-opened it would land on the older one after reload.
    page.get_by_test_id("thread-item").nth(1).click()
    older_title = page.get_by_test_id("thread-item").nth(1).inner_text().strip()
    expect(page.get_by_test_id("current-thread-title")).to_have_text(
        re.compile(re.escape(older_title))
    )
    # Reload — must land on the newest (top row), not the last-opened one.
    page.reload()
    newest_title = page.get_by_test_id("thread-item").first.inner_text().strip()
    expect(page.get_by_test_id("current-thread-title")).to_have_text(
        re.compile(re.escape(newest_title))
    )
    expect(page.get_by_test_id("thread-item").first).to_have_attribute(
        "data-active", "true"
    )


# AC-123: reload after deleting the current thread opens the newest remaining
def test_reload_after_current_deleted_opens_newest_remaining(
    page: Page, app_url: str
) -> None:
    page.goto(app_url)
    _send(page, "keeper thread")
    _await_reply(page)
    page.get_by_test_id("new-thread-btn").click()
    _send(page, "doomed thread")
    _await_reply(page)
    # Delete the newest (currently active)
    items = page.get_by_test_id("thread-item")
    items.first.hover()
    page.get_by_test_id("thread-delete-btn").first.click()
    page.get_by_test_id("delete-confirm").click()
    expect(page.get_by_test_id("thread-item")).to_have_count(1)
    # Reload — must land on the remaining keeper, not attempt to restore
    # the deleted thread.
    page.reload()
    expect(page.get_by_test_id("thread-item")).to_have_count(1)
    keeper_title = page.get_by_test_id("thread-item").first.inner_text().strip()
    expect(page.get_by_test_id("current-thread-title")).to_have_text(
        re.compile(re.escape(keeper_title))
    )
    expect(page.get_by_test_id("thread-item").first).to_have_attribute(
        "data-active", "true"
    )


# AC-125: titles render as text, never as HTML (XSS guard)
def test_title_renders_as_text_not_html(page: Page, app_url: str) -> None:
    page.goto(app_url)
    _send(page, "seed message")
    _await_reply(page)
    page.get_by_test_id("current-thread-title").click()
    box = page.get_by_test_id("current-thread-title-input")
    box.fill("<img src=x onerror=window.__pwned=1>")
    box.press("Enter")
    # Header title contains the literal text (not the rendered <img>)
    expect(page.get_by_test_id("current-thread-title")).to_contain_text(
        "<img src=x onerror=window.__pwned=1>"
    )
    # No injected DOM element and no executed handler. querySelectorAll is
    # inside page.evaluate() so it is not a Playwright selector call — no
    # INV-4 raw-selector rejection, and the assertion still verifies the
    # HTML wasn't parsed as HTML.
    injected = page.evaluate(
        "document.querySelectorAll('img[src=\"x\"]').length"
    )
    assert injected == 0, "title must not be parsed as HTML"
    assert page.evaluate("window.__pwned") is None, (
        "title's onerror handler must not have executed"
    )


# AC-126: newlines are stripped from a header-title commit
def test_newlines_in_header_title_are_stripped_on_commit(
    page: Page, app_url: str
) -> None:
    page.goto(app_url)
    _send(page, "seed message")
    _await_reply(page)
    page.get_by_test_id("current-thread-title").click()
    box = page.get_by_test_id("current-thread-title-input")
    # A contenteditable / input receiving Shift+Enter or Enter within its
    # text would produce a newline in the buffer; we simulate by directly
    # setting the value including a newline character and pressing Enter to
    # commit. The commit path must strip.
    box.fill("line one\nline two")
    box.press("Enter")
    committed = page.get_by_test_id("current-thread-title").inner_text()
    assert "\n" not in committed, (
        f"committed title contains a raw newline: {committed!r}"
    )
    # And the sidebar carries the same single-line rendering
    assert "\n" not in page.get_by_test_id("thread-item").first.inner_text()


# =============================================================================
# v65 catch-up (AC-127..AC-132) — behaviors shipped in the M31 hand-build.
#
# Provenance (PRD v65 caveat): these six tests were written AFTER the
# implementation, by its author. They are regression pins on as-built
# behavior, not an independent oracle for it.
# =============================================================================


# AC-127: titles are stored full-length; shortening is render-time only
def test_thread_title_stores_full_text_beyond_thirty_chars(
    page: Page, app_url: str
) -> None:
    long_msg = (
        "chronicle of an unusually verbose opening message that would have "
        "been cut at thirty characters before v65"
    )
    page.goto(app_url)
    _send(page, long_msg)
    _await_reply(page)
    # Sidebar row carries the full stored text (CSS may clip the paint;
    # the text itself is intact).
    expect(page.get_by_test_id("thread-item").first).to_contain_text(long_msg)
    # Header tooltip carries the same full string.
    expect(page.get_by_test_id("current-thread-title")).to_have_attribute(
        "title", long_msg
    )
    # And no truncation marker was baked into storage.
    row_text = page.get_by_test_id("thread-item").first.inner_text()
    assert not row_text.strip().endswith("..."), (
        f"stored title must not end in a baked ellipsis: {row_text!r}"
    )


# AC-128: a history-restored reply's copy source is reasoning-free
def test_reply_copy_source_strips_think_after_reload(
    page: Page, app_url: str
) -> None:
    page.goto(app_url)
    _send(page, "seed for copy provenance")
    _await_reply(page)
    page.reload()
    expect(page.get_by_test_id("msg-assistant").first).to_be_visible()
    # Fixture sanity: the stub stream embeds inline <think>...</think>, so
    # the stored message MUST carry markup for this test to bite.
    stored_has_think = page.evaluate(
        "window.TC.threads.some(t => t.messages.some("
        "m => m.role === 'assistant' && m.content.includes('<think>')))"
    )
    assert stored_has_think, (
        "fixture reply no longer carries inline <think> — this test needs a "
        "stream shape that exercises the strip path"
    )
    raw = page.evaluate(
        "document.querySelector('[data-testid=\"msg-assistant\"]').dataset.raw"
    )
    assert "<think>" not in raw, f"copy source carries reasoning markup: {raw[:80]!r}"
    assert "Hello" in raw, "copy source lost the reply's visible text"


# AC-129: the divider drags, and width clamps at half the viewport
def test_sidebar_divider_drags_and_clamps(page: Page, app_url: str) -> None:
    page.goto(app_url)
    handle = page.get_by_test_id("sidebar-resizer")
    box = handle.bounding_box()
    assert box is not None
    grab_y = box["y"] + 200
    page.mouse.move(box["x"] + box["width"] / 2, grab_y)
    page.mouse.down()
    page.mouse.move(400, grab_y, steps=4)
    page.mouse.up()
    width = page.evaluate(
        "document.querySelector('.sidebar').getBoundingClientRect().width"
    )
    assert abs(width - 400) <= 6, f"drag to 400px landed at {width}px"
    # Drag far past the middle — must clamp to viewport/2.
    box = handle.bounding_box()
    assert box is not None
    page.mouse.move(box["x"] + box["width"] / 2, grab_y)
    page.mouse.down()
    page.mouse.move(1200, grab_y, steps=4)
    page.mouse.up()
    width = page.evaluate(
        "document.querySelector('.sidebar').getBoundingClientRect().width"
    )
    half = page.evaluate("Math.round(window.innerWidth / 2)")
    assert width <= half + 2, f"width {width}px escaped the half-viewport clamp {half}px"
    assert width >= half - 6, f"width {width}px stopped short of the clamp {half}px"


# AC-129: the chosen width survives a reload
def test_sidebar_width_persists_across_reload(page: Page, app_url: str) -> None:
    page.goto(app_url)
    handle = page.get_by_test_id("sidebar-resizer")
    box = handle.bounding_box()
    assert box is not None
    grab_y = box["y"] + 200
    page.mouse.move(box["x"] + box["width"] / 2, grab_y)
    page.mouse.down()
    page.mouse.move(380, grab_y, steps=4)
    page.mouse.up()
    before = page.evaluate(
        "document.querySelector('.sidebar').getBoundingClientRect().width"
    )
    assert abs(before - 380) <= 6
    page.reload()
    expect(page.get_by_test_id("sidebar-resizer")).to_be_visible()
    after = page.evaluate(
        "document.querySelector('.sidebar').getBoundingClientRect().width"
    )
    assert abs(after - before) <= 2, (
        f"width did not persist across reload: {before}px -> {after}px"
    )


# AC-130 / AC-131: nothing loaded -> placeholder voice; Send guides, not 422
def test_no_loaded_model_shows_placeholder_and_send_guides(
    page: Page, app_url: str
) -> None:
    page.route(
        "**/api/v1/models",
        lambda route: route.fulfill(
            status=200, content_type="application/json", body='{"models":[]}'
        ),
    )
    page.route(
        "**/api/v1/models/catalog",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"models":[{"id":"nemotron","source":"nemotron","loaded":false}]}',
        ),
    )
    page.goto(app_url)
    select = page.get_by_test_id("model-select")
    expect(select).to_have_value("")
    shown = page.evaluate(
        "document.querySelector('[data-testid=\"model-select\"]')"
        ".selectedOptions[0].textContent"
    )
    assert "Select model" in shown, f"placeholder option not shown: {shown!r}"
    # The M28 status rule already disables the Send button without a loaded
    # model — pin that, then exercise the Enter path (form.requestSubmit
    # bypasses the disabled submitter), which must guide, not 422.
    expect(page.get_by_test_id("send-btn")).to_be_disabled()
    page.get_by_test_id("message-input").fill("hello without a model")
    page.get_by_test_id("message-input").press("Enter")
    expect(page.get_by_test_id("msg-error")).to_contain_text("Pick a model")
    expect(page.get_by_test_id("msg-user")).to_have_count(0)


# AC-132: picking an unloaded model asks first; cancel reverts and sends nothing
def test_unloaded_model_pick_asks_and_cancel_reverts(
    page: Page, app_url: str
) -> None:
    page.route(
        "**/api/v1/models",
        lambda route: route.fulfill(
            status=200, content_type="application/json", body='{"models":[]}'
        ),
    )
    page.route(
        "**/api/v1/models/catalog",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"models":[{"id":"nemotron","source":"nemotron","loaded":false}]}',
        ),
    )
    page.goto(app_url)
    select = page.get_by_test_id("model-select")
    expect(select).to_have_value("")
    select.select_option("nemotron")
    expect(page.get_by_test_id("load-confirm-modal")).to_be_visible()
    page.get_by_test_id("load-cancel").click()
    expect(page.get_by_test_id("load-confirm-modal")).to_be_hidden()
    # Reverted to the prior (placeholder) selection; nothing loaded or sent.
    expect(select).to_have_value("")
    expect(page.get_by_test_id("msg-user")).to_have_count(0)


# =============================================================================
# M32 (spec v67) — free model selection across threads
#
# AC-28 (per-thread model lock) is retired. The dropdown is enabled at all
# times; picking a different model on any thread — including one with prior
# messages — updates that thread's stored model and routes subsequent sends
# to the pick. Per-thread stickiness on switch is preserved.
# =============================================================================


# AC-133 [M32 — the selector is enabled at all times, on every thread,
# replacing the retired AC-28 mid-chat lock]
def test_selector_stays_enabled_across_all_ui_states(page: Page, app_url: str) -> None:
    page.goto(app_url)
    select = page.get_by_test_id("model-select")
    # initial page load
    expect(select).to_be_enabled()
    # after send + reply (previously locked under AC-28)
    _send(page, "first turn")
    _await_reply(page)
    expect(select).to_be_enabled()
    # after opening a new chat
    page.get_by_test_id("new-thread-btn").click()
    expect(select).to_be_enabled()
    # after switching back to the sent thread
    page.get_by_test_id("thread-item").nth(1).click()
    expect(select).to_be_enabled()
    # after reload (previously the persisted locked=true forced disabled)
    page.reload()
    expect(select).to_be_enabled()


# AC-134 [M32 — thread switch restores that thread's stored model in the
# selector; per-thread sticky behavior]
def test_thread_switch_restores_stored_model(page: Page, app_url: str) -> None:
    page.goto(app_url)
    select = page.get_by_test_id("model-select")
    expect(select).to_have_value("alpha-model")  # default
    _send(page, "thread one uses alpha")
    _await_reply(page)
    # open a second thread and pick beta there
    page.get_by_test_id("new-thread-btn").click()
    select.select_option("beta-model")
    _send(page, "thread two uses beta")
    _await_reply(page)
    # switch back to thread 1 — dropdown restores alpha
    page.get_by_test_id("thread-item").nth(1).click()
    expect(select).to_have_value("alpha-model")
    # switch to thread 2 — dropdown restores beta
    page.get_by_test_id("thread-item").first.click()
    expect(select).to_have_value("beta-model")


# AC-135 [M32 — picking a different model on a thread with prior messages
# updates that thread's stored model; subsequent sends route to the pick;
# reload shows the picked model in the selector]
def test_mid_chat_switch_updates_thread_model_and_routes_next_send(
    page: Page, app_url: str, last_chat_request
) -> None:
    page.goto(app_url)
    select = page.get_by_test_id("model-select")
    expect(select).to_have_value("alpha-model")
    _send(page, "first turn on alpha")
    _await_reply(page)
    req = last_chat_request()
    assert req["model"] == "alpha-model", (
        f"first send should carry alpha, got {req.get('model')!r}"
    )
    # user switches to beta mid-chat (previously blocked by AC-28)
    select.select_option("beta-model")
    _send(page, "second turn on beta")
    _await_reply(page, 2)
    req = last_chat_request()
    assert req["model"] == "beta-model", (
        f"post-switch send should route to beta, got {req.get('model')!r}"
    )
    # reload — the switched model is persisted for this thread
    page.reload()
    expect(select).to_have_value("beta-model")
