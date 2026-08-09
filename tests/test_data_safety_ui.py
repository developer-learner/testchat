"""Frozen browser oracles for the v88 conversation data-safety milestone."""

import json
import urllib.request

from playwright.sync_api import Page, expect


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


def test_delete_one_thread_survives_reload(page: Page, app_url: str) -> None:
    survivors = [_thread(1101, "alpha survivor"), _thread(1103, "gamma survivor")]
    _seed_threads(app_url, [survivors[0], _thread(1102, "delete only me"), survivors[1]])
    page.add_init_script(
        """
        (function () {
          var nativeFetch = window.fetch.bind(window);
          var finish;
          window.__tcMutationFinished = new Promise(function (resolve) { finish = resolve; });
          window.fetch = function (input, init) {
            var url = typeof input === 'string' ? input : input.url;
            var method = ((init && init.method) || (input && input.method) || 'GET').toUpperCase();
            var result = nativeFetch(input, init);
            if (url.endsWith('/api/v1/threads') && (method === 'PUT' || method === 'DELETE')) {
              return result.then(function (response) {
                finish({method: method, status: response.status});
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
    page.get_by_test_id("thread-delete-btn").nth(1).click()
    page.get_by_test_id("delete-confirm").click()
    mutation = page.evaluate("window.__tcMutationFinished")
    page.reload()

    items = page.get_by_test_id("thread-item")
    expect(items).to_have_count(2)
    visible_titles = items.all_text_contents()
    stored = _request_json(f"{app_url}/api/v1/threads")

    assert (
        mutation,
        [thread["id"] for thread in stored["threads"]],
        all(title in " ".join(visible_titles) for title in ("alpha survivor", "gamma survivor")),
    ) == ({"method": "PUT", "status": 200}, [1101, 1103], True)


def test_hydration_failure_warns_retries_and_recovers_saving(
    page: Page,
    app_url: str,
) -> None:
    _seed_threads(app_url, [_thread(1201, "saved before outage")])
    page.add_init_script(
        """
        (function () {
          var nativeFetch = window.fetch.bind(window);
          var state = {gets: 0, puts: 0};
          state.release = new Promise(function (resolve) { state.releaseRetry = resolve; });
          state.putSeen = new Promise(function (resolve) { state.resolvePut = resolve; });
          window.__tcHydration = state;
          window.fetch = function (input, init) {
            var url = typeof input === 'string' ? input : input.url;
            var method = ((init && init.method) || (input && input.method) || 'GET').toUpperCase();
            if (url.endsWith('/api/v1/threads') && method === 'GET') {
              state.gets += 1;
              if (state.gets <= 2) {
                return Promise.reject(new TypeError('synthetic hydration outage'));
              }
              if (state.gets === 3) {
                return state.release.then(function () { return nativeFetch(input, init); });
              }
            }
            var result = nativeFetch(input, init);
            if (url.endsWith('/api/v1/threads') && method === 'PUT') {
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
    persisted = page.evaluate("window.__tcHydration.putSeen")
    expect(page.get_by_test_id("thread-item")).to_have_count(2)
    stored = _request_json(f"{app_url}/api/v1/threads")

    assert (
        persisted,
        page.evaluate("window.__tcHydration.gets") >= 3,
        len(stored["threads"]),
        stored["threads"][0]["title"],
    ) == ({"method": "PUT", "status": 200}, True, 2, "saved before outage")
