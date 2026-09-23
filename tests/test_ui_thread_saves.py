"""Per-thread saving — browser oracle (AC-199, AC-204).

AC-199 uses a fetch stub (contracts.ui testids only, Promise barriers, no
sleeps). AC-204 runs two real tabs against the real app: two tabs that loaded
the same history each edit a DIFFERENT chat, and both edits survive.
"""
import json
import urllib.request

from playwright.sync_api import Page, expect


def _wait(page: Page, promise_js: str, ms: int = 10000):
    """Await an in-page promise, failing fast instead of hanging the suite."""
    label = json.dumps(promise_js)
    return page.evaluate(
        f"""() => Promise.race([
            Promise.resolve({promise_js}),
            new Promise((_, reject) => setTimeout(
                () => reject(new Error('timed out after {ms} ms: ' + {label})), {ms}))
        ])"""
    )


def _request_json(url: str, method: str = "GET", payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(
        url,
        method=method,
        data=data,
        headers={"Content-Type": "application/json"} if data is not None else {},
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read())


def _thread(thread_id: int, title: str) -> dict:
    return {"id": thread_id, "title": title, "messages": [], "model": "", "locked": False}


def _seed_threads(app_url: str, threads: list[dict]) -> None:
    revision = _request_json(f"{app_url}/api/v1/threads")["revision"]
    _request_json(
        f"{app_url}/api/v1/threads",
        method="PUT",
        payload={"revision": revision, "threads": threads},
    )


def _rename_row(page: Page, index: int, title: str) -> None:
    row = page.get_by_test_id("thread-item").nth(index)
    row.hover()
    row.get_by_test_id("thread-rename-btn").click()
    box = page.get_by_test_id("thread-rename-input")
    box.fill(title)
    box.press("Enter")


def _install_single_thread_stub(page: Page) -> None:
    page.add_init_script(
        """
        const nativeFetch = window.fetch.bind(window);
        const stub = {puts: [], waiters: []};
        stub.waitForPuts = function(count) {
          if (stub.puts.length >= count) return Promise.resolve(stub.puts);
          return new Promise(resolve => stub.waiters.push({count, resolve}));
        };
        window.__saveStub = stub;
        window.fetch = function(input, init) {
          const url = typeof input === 'string' ? input : input.url;
          const method = String((init && init.method) || input.method || 'GET').toUpperCase();
          if (url.endsWith('/api/v1/threads') && method === 'GET') {
            return Promise.resolve(new Response(JSON.stringify({
              threads: [
                {id: 1, title: 'Older chat', messages: [], model: 'alpha-model', locked: false, revision: 3},
                {id: 2, title: 'Newer chat', messages: [], model: 'alpha-model', locked: false, revision: 5}
              ],
              revision: 9,
              quarantined: false
            }), {status: 200, headers: {'Content-Type': 'application/json'}}));
          }
          if (/\\/api\\/v1\\/threads(\\/\\d+)?$/.test(url) && method !== 'GET') {
            const body = JSON.parse(init.body);
            stub.puts.push({method, path: new URL(url, location.href).pathname, body});
            const rev = body.revision + 1;
            const ready = stub.waiters.filter(w => stub.puts.length >= w.count);
            stub.waiters = stub.waiters.filter(w => stub.puts.length < w.count);
            ready.forEach(w => w.resolve(stub.puts));
            return Promise.resolve(new Response(JSON.stringify({status: 'ok', revision: rev}),
              {status: 200, headers: {'Content-Type': 'application/json'}}));
          }
          return nativeFetch(input, init);
        };
        """
    )


# AC-199 — editing one chat sends only that chat, with that chat's revision.
def test_editing_one_chat_saves_only_that_chat(page: Page, app_url: str) -> None:
    _install_single_thread_stub(page)
    page.goto(app_url)
    expect(page.get_by_test_id("thread-item")).to_have_count(2)

    _rename_row(page, 1, "Older chat renamed")  # sidebar is newest-first
    _rename_row(page, 1, "Older chat renamed twice")
    saves = _wait(page, "window.__saveStub.waitForPuts(2)")

    assert [(s["method"], s["path"]) for s in saves] == [
        ("PUT", "/api/v1/threads/1"),
        ("PUT", "/api/v1/threads/1"),
    ]
    assert [s["body"]["revision"] for s in saves] == [3, 4]
    assert [s["body"]["thread"]["title"] for s in saves] == [
        "Older chat renamed",
        "Older chat renamed twice",
    ]
    assert all("threads" not in s["body"] for s in saves)
    expect(page.get_by_test_id("save-status")).to_have_text("")


_SAVE_WATCH = """
(function () {
  var nativeFetch = window.fetch.bind(window);
  window.__saves = [];
  window.__saveWaiters = [];
  window.__waitForSaves = function (count) {
    if (window.__saves.length >= count) return Promise.resolve(window.__saves);
    return new Promise(function (resolve) { window.__saveWaiters.push({count: count, resolve: resolve}); });
  };
  window.fetch = function (input, init) {
    var url = typeof input === 'string' ? input : input.url;
    var method = ((init && init.method) || (input && input.method) || 'GET').toUpperCase();
    var result = nativeFetch(input, init);
    if (/\\/api\\/v1\\/threads(\\/\\d+)?$/.test(url) && method !== 'GET') {
      return result.then(function (response) {
        window.__saves.push({method: method, path: new URL(url, location.href).pathname, status: response.status});
        var ready = window.__saveWaiters.filter(function (w) { return window.__saves.length >= w.count; });
        window.__saveWaiters = window.__saveWaiters.filter(function (w) { return window.__saves.length < w.count; });
        ready.forEach(function (w) { w.resolve(window.__saves); });
        return response;
      });
    }
    return result;
  };
})();
"""


# AC-204 — two tabs editing different chats: no warning, both edits survive.
def test_two_tabs_editing_different_chats_both_persist(page: Page, app_url: str) -> None:
    _seed_threads(app_url, [_thread(1301, "chat one"), _thread(1302, "chat two")])
    page.context.add_init_script(_SAVE_WATCH)
    tab_a = page
    tab_b = page.context.new_page()
    tab_a.goto(app_url)
    tab_b.goto(app_url)
    expect(tab_a.get_by_test_id("thread-item")).to_have_count(2)
    expect(tab_b.get_by_test_id("thread-item")).to_have_count(2)

    _rename_row(tab_a, 1, "one by tab A")  # row 1 = chat one (newest-first)
    saves_a = _wait(tab_a, "window.__waitForSaves(1)")
    _rename_row(tab_b, 0, "two by tab B")  # row 0 = chat two
    saves_b = _wait(tab_b, "window.__waitForSaves(1)")

    assert saves_a == [{"method": "PUT", "path": "/api/v1/threads/1301", "status": 200}]
    assert saves_b == [{"method": "PUT", "path": "/api/v1/threads/1302", "status": 200}]
    expect(tab_a.get_by_test_id("save-status")).to_have_text("")
    expect(tab_b.get_by_test_id("save-status")).to_have_text("")

    tab_b.reload()
    titles = " ".join(tab_b.get_by_test_id("thread-item").all_text_contents())
    stored = {t["id"]: t["title"] for t in _request_json(f"{app_url}/api/v1/threads")["threads"]}
    assert ("one by tab A" in titles, "two by tab B" in titles) == (True, True)
    assert stored == {1301: "one by tab A", 1302: "two by tab B"}
    tab_b.close()
