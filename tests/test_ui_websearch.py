"""Frozen UI suite addition (D-58) — M25 web-informed answers, AC-84/88/91.

Element location: contracts.ui testids ONLY. Synchronization: Playwright
auto-waiting via expect() ONLY. Zero retries. The app under test runs
configured (conftest points TAVILY_ENDPOINT at the stub, which returns
two capture-shaped sources for every search).
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


# AC-84 — toggle exists, default off, enabled (app under test is configured)
def test_web_toggle_present_default_off(page: Page, app_url: str) -> None:
    page.goto(app_url)
    toggle = page.get_by_test_id("web-toggle")
    expect(toggle).to_be_visible()
    expect(toggle).to_be_enabled()
    expect(toggle).not_to_have_class(re.compile(r"\bactive\b"))


# AC-84/88 — armed send renders numbered source links; toggle resets;
# the NEXT unarmed send carries no sources
def test_web_reply_shows_source_links_and_toggle_resets(
    page: Page, app_url: str
) -> None:
    page.goto(app_url)
    toggle = page.get_by_test_id("web-toggle")
    toggle.click()
    expect(toggle).to_have_class(re.compile(r"\bactive\b"))
    _send(page, "what is new")
    _await_reply(page)
    expect(page.get_by_test_id("msg-sources")).to_have_count(1)
    links = page.get_by_test_id("source-link")
    expect(links).to_have_count(2)
    expect(links.nth(0)).to_contain_text("[1]")
    expect(links.nth(0)).to_have_attribute("href", "https://example.org/one")
    expect(links.nth(1)).to_have_attribute("href", "https://example.org/two")
    expect(toggle).not_to_have_class(re.compile(r"\bactive\b"))
    _send(page, "and offline now")
    _await_reply(page, count=2)
    expect(page.get_by_test_id("msg-sources")).to_have_count(1)


# AC-91 — sources survive persistence and re-render after a reload
def test_sources_persist_across_reload(page: Page, app_url: str) -> None:
    page.goto(app_url)
    page.get_by_test_id("web-toggle").click()
    _send(page, "what is new")
    _await_reply(page)
    expect(page.get_by_test_id("source-link")).to_have_count(2)
    page.goto(app_url)
    # locate by title (first message titles the thread) — a fresh page
    # load may seat an empty New Chat at the top of the newest-first list
    page.get_by_test_id("thread-item").filter(has_text="what is new").click()
    links = page.get_by_test_id("source-link")
    expect(links).to_have_count(2)
    expect(links.nth(0)).to_have_attribute("href", "https://example.org/one")


# AC-92 (M26 ratify) — Qwen full-width citation markers like 【1†L1-L3】 must
# render as [1]. Seed a prepared message via the locked PUT route so the
# test doesn't depend on the LLM stub's output shape.
def test_full_width_citation_markers_render_as_plain_brackets(
    page: Page, app_url: str
) -> None:
    import json
    import urllib.request

    raw = "The latest release is Python 3.14 【1†L1-L3】【4†L1-L4】."
    payload = {
        "threads": [
            {
                "id": 1,
                "title": "ratify",
                "model": "",
                "locked": False,
                "messages": [
                    {"role": "user", "content": "python?", "ts": 1.0, "model": ""},
                    {"role": "assistant", "content": raw, "ts": 2.0, "model": "m"},
                ],
            }
        ]
    }
    with urllib.request.urlopen(f"{app_url}/api/v1/threads", timeout=5) as response:
        payload["revision"] = json.loads(response.read())["revision"]
    req = urllib.request.Request(
        f"{app_url}/api/v1/threads",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="PUT",
    )
    urllib.request.urlopen(req, timeout=5).read()
    page.goto(app_url)
    page.get_by_test_id("thread-item").filter(has_text="ratify").click()
    reply = page.get_by_test_id("msg-assistant").first
    expect(reply).to_contain_text("[1]")
    expect(reply).to_contain_text("[4]")
    expect(reply).not_to_contain_text("【")
    expect(reply).not_to_contain_text("】")
