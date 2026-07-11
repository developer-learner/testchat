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
    page.get_by_test_id("thread-item").nth(0).click()
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
    page.get_by_test_id("thread-item").nth(0).click()
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
    page.goto(app_url)
    select = page.get_by_test_id("model-select")
    expect(select).to_have_value("alpha-model")
    stamp = re.search(r"refresh-(\d+)", select.inner_text())
    assert stamp, "stub stamps every models response with refresh-N"
    n = int(stamp.group(1))
    select.select_option("beta-model")
    page.get_by_test_id("unload-nemotron").click()
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
    page.get_by_test_id("thread-item").nth(0).click()
    expect(page.get_by_test_id("msg-user")).to_have_count(1)
    expect(page.get_by_test_id("msg-user").first).to_contain_text("this must not vanish")


# AC-42 [M9 — "thinking..." placeholder before visible answer text]
def test_thinking_placeholder_shows_then_clears(page: Page, app_url: str) -> None:
    page.goto(app_url)
    # SLOWPING routes the stub to: think tokens, flush, hold ~1.2s, then the
    # visible answer. Auto-wait observes the placeholder window without any
    # timing assertion in the test (D-58 determinism).
    _send(page, "SLOWPING please think first")
    reply = page.get_by_test_id("msg-assistant").last
    expect(reply).to_contain_text("thinking...")        # visible during the hold
    expect(reply).to_contain_text("Hello there")        # answer replaces it
    expect(reply).not_to_contain_text("thinking...")    # placeholder is gone
