"""Frozen browser oracles for the v88 conversation data-safety milestone.

v127: a single-chat delete is its own per-thread DELETE (AC-202 supersedes
AC-156/AC-157); hydration recovery (AC-158) now observes a per-thread save.
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
    return {
        "id": thread_id,
        "title": title,
        "messages": [],
        "model": "",
        "locked": False,
    }


def _seed_threads(app_url: str, threads: list[dict]) -> None:
    revision = _request_json(f"{app_url}/api/v1/threads")["revision"]
    _request_json(
        f"{app_url}/api/v1/threads",
        method="PUT",
        payload={"revision": revision, "threads": threads},
    )


# AC-202 — deleting one chat sends only its per-thread DELETE.
def test_delete_one_thread_survives_reload(page: Page, app_url: str) -> None:
    survivors = [_thread(1101, "alpha survivor"), _thread(1103, "gamma survivor")]
    _seed_threads(app_url, [survivors[0], _thread(1102, "delete only me"), survivors[1]])
    page.add_init_script(
        """
        (function () {
          var nativeFetch = window.fetch.bind(window);
          var finish;
          window.__tcMutations = [];
          window.__tcMutationFinished = new Promise(function (resolve) { finish = resolve; });
          window.fetch = function (input, init) {
            var url = typeof input === 'string' ? input : input.url;
            var method = ((init && init.method) || (input && input.method) || 'GET').toUpperCase();
            var result = nativeFetch(input, init);
            if (/\\/api\\/v1\\/threads(\\/\\d+)?$/.test(url) && (method === 'PUT' || method === 'DELETE')) {
              var path = new URL(url, location.href).pathname;
              window.__tcMutations.push({method: method, path: path});
              return result.then(function (response) {
                if (method === 'DELETE') finish({method: method, path: path, status: response.status});
                return response;
              });
            }
            return result;
          };
        })();
        """
    )

    page.goto(app_url)
    expect(page.get_by_test_id("thread-item")).to_have_count(3)
    owning_row = page.get_by_test_id("thread-item").nth(1)
    owning_row.hover()
    owning_row.get_by_test_id("thread-delete-btn").click()
    page.get_by_test_id("delete-confirm").click()
    mutation = _wait(page, "window.__tcMutationFinished")
    whole_history_writes = page.evaluate(
        "window.__tcMutations.filter(m => m.path === '/api/v1/threads').length"
    )
    page.reload()

    items = page.get_by_test_id("thread-item")
    expect(items).to_have_count(2)
    visible_titles = items.all_text_contents()
    stored = _request_json(f"{app_url}/api/v1/threads")

    assert (
        mutation,
        whole_history_writes,
        [thread["id"] for thread in stored["threads"]],
        all(title in " ".join(visible_titles) for title in ("alpha survivor", "gamma survivor")),
    ) == (
        {"method": "DELETE", "path": "/api/v1/threads/1102", "status": 200},
        0,
        [1101, 1103],
        True,
    )


def test_hydration_failure_warns_retries_and_recovers_saving(
    page: Page,
    app_url: str,
) -> None:
    _seed_threads(app_url, [_thread(1201, "saved before outage")])
    page.add_init_script(
        """
        (function () {
          var nativeFetch = window.fetch.bind(window);
          var state = {hydrationGets: 0, puts: 0};
          state.release = new Promise(function (resolve) { state.releaseRetry = resolve; });
          state.putSeen = new Promise(function (resolve) { state.resolvePut = resolve; });
          window.__tcHydration = state;
          window.fetch = function (input, init) {
            var url = typeof input === 'string' ? input : input.url;
            var method = ((init && init.method) || (input && input.method) || 'GET').toUpperCase();
            var caller = (new Error()).stack || '';
            var isHydration = caller.indexOf('/static/app.js') !== -1;
            if (url.endsWith('/api/v1/threads') && method === 'GET' && isHydration) {
              state.hydrationGets += 1;
              if (state.hydrationGets === 1) {
                return Promise.reject(new TypeError('synthetic hydration outage'));
              }
              if (state.hydrationGets === 2) {
                return state.release.then(function () { return nativeFetch(input, init); });
              }
            }
            var result = nativeFetch(input, init);
            if (/\\/api\\/v1\\/threads(\\/\\d+)?$/.test(url) && method === 'PUT') {
              state.puts += 1;
              return result.then(function (response) {
                state.resolvePut({method: method, status: response.status});
                return response;
              });
            }
            return result;
          };
        })();
        """
    )

    page.goto(app_url)
    expect(page.get_by_test_id("history-status")).to_have_text(
        "history unavailable — retrying"
    )
    page.evaluate("window.__tcHydration.releaseRetry()")
    expect(page.get_by_test_id("thread-item")).to_have_count(1)
    expect(page.get_by_test_id("history-status")).to_have_text("")

    page.get_by_test_id("new-thread-btn").click()
    persisted = _wait(page, "window.__tcHydration.putSeen")
    expect(page.get_by_test_id("thread-item")).to_have_count(2)
    stored = _request_json(f"{app_url}/api/v1/threads")

    assert (
        persisted,
        page.evaluate("window.__tcHydration.hydrationGets") >= 2,
        len(stored["threads"]),
        stored["threads"][0]["title"],
    ) == ({"method": "PUT", "status": 200}, True, 2, "saved before outage")
