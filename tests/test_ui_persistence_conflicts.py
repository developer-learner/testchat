"""Browser oracle: ordered per-thread saves, conflict latch, reload recovery.

M33 introduced ordered saves and the conflict latch over whole-history saves;
v127 moves saving to one chat per request (AC-200 supersedes AC-146, AC-201
supersedes AC-147; AC-148 is carried). Element location uses contracts.ui
testids only. Synchronization uses explicit Promise barriers fired by captured
saves or committed title mutations; there are no sleeps, guessed microtask
turns, or retry allowances.
"""
import json

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


def _rename(page: Page, title: str) -> None:
    page.get_by_test_id("current-thread-title").click()
    page.get_by_test_id("current-thread-title-input").fill(title)
    page.get_by_test_id("current-thread-title-input").press("Enter")


def _install_queue_stub(page: Page) -> None:
    page.add_init_script(
        """
        const nativeFetch = window.fetch.bind(window);
        const stub = {puts: [], resolvers: [], putWaiters: []};
        stub.notifyPuts = function() {
          const ready = stub.putWaiters.filter(w => stub.puts.length >= w.count);
          stub.putWaiters = stub.putWaiters.filter(w => stub.puts.length < w.count);
          ready.forEach(w => w.resolve(stub.puts));
        };
        stub.waitForPuts = function(count) {
          if (stub.puts.length >= count) return Promise.resolve(stub.puts);
          return new Promise(resolve => stub.putWaiters.push({count, resolve}));
        };
        stub.respond = function(index, status, body) {
          stub.resolvers[index](new Response(JSON.stringify(body), {
            status,
            headers: {'Content-Type': 'application/json'}
          }));
        };
        window.__m33Stub = stub;
        window.fetch = function(input, init) {
          const url = typeof input === 'string' ? input : input.url;
          const method = String((init && init.method) || input.method || 'GET').toUpperCase();
          if (url.endsWith('/api/v1/threads') && method === 'GET') {
            return Promise.resolve(new Response(JSON.stringify({
              threads: [{id: 1, title: 'Initial', messages: [], model: 'alpha-model', locked: false, revision: 7}],
              revision: 12,
              quarantined: false
            }), {status: 200, headers: {'Content-Type': 'application/json'}}));
          }
          if (/\\/api\\/v1\\/threads\\/\\d+$/.test(url) && method === 'PUT') {
            stub.puts.push({path: new URL(url, location.href).pathname, body: JSON.parse(init.body)});
            stub.notifyPuts();
            return new Promise(resolve => stub.resolvers.push(resolve));
          }
          return nativeFetch(input, init);
        };
        """
    )


# AC-200 — rapid edits to a chat wait for its prior accepted revision.
def test_browser_serializes_rapid_mutations_in_revision_order(
    page: Page, app_url: str
) -> None:
    _install_queue_stub(page)
    page.goto(app_url)
    expect(page.get_by_test_id("current-thread-title")).to_have_text("Initial")

    _rename(page, "First mutation")
    _rename(page, "Second mutation")
    puts = _wait(page, "window.__m33Stub.waitForPuts(1)")
    assert len(puts) == 1
    assert puts[0]["path"] == "/api/v1/threads/1"
    assert puts[0]["body"]["revision"] == 7
    assert puts[0]["body"]["thread"]["title"] == "First mutation"

    puts = _wait(
        page,
        "(() => { const barrier = window.__m33Stub.waitForPuts(2); "
        "window.__m33Stub.respond(0, 200, {status: 'ok', revision: 8}); "
        "return barrier; })()",
    )
    assert len(puts) == 2
    assert puts[1]["body"]["revision"] == 8
    assert puts[1]["body"]["thread"]["title"] == "Second mutation"
    page.evaluate(
        "() => window.__m33Stub.respond(1, 200, {status: 'ok', revision: 9})"
    )


def _install_conflict_stub(page: Page) -> None:
    page.add_init_script(
        """
        const nativeFetch = window.fetch.bind(window);
        const stub = {puts: [], putWaiters: []};
        stub.notifyPuts = function() {
          const ready = stub.putWaiters.filter(w => stub.puts.length >= w.count);
          stub.putWaiters = stub.putWaiters.filter(w => stub.puts.length < w.count);
          ready.forEach(w => w.resolve(stub.puts));
        };
        stub.waitForPuts = function(count) {
          if (stub.puts.length >= count) return Promise.resolve(stub.puts);
          return new Promise(resolve => stub.putWaiters.push({count, resolve}));
        };
        stub.waitForTitle = function(title) {
          const read = () => {
            const node = document.querySelector('[data-testid="current-thread-title"]');
            return node ? node.textContent : null;
          };
          if (read() === title) return Promise.resolve();
          return new Promise(resolve => {
            const observer = new MutationObserver(() => {
              if (read() === title) { observer.disconnect(); resolve(); }
            });
            observer.observe(document.documentElement, {subtree: true, childList: true, characterData: true});
          });
        };
        window.__m33Stub = stub;
        window.fetch = function(input, init) {
          const url = typeof input === 'string' ? input : input.url;
          const method = String((init && init.method) || input.method || 'GET').toUpperCase();
          if (url.endsWith('/api/v1/threads') && method === 'GET') {
            return Promise.resolve(new Response(JSON.stringify({
              threads: [{id: 1, title: 'Initial', messages: [], model: 'alpha-model', locked: false, revision: 3}],
              revision: 3,
              quarantined: false
            }), {status: 200, headers: {'Content-Type': 'application/json'}}));
          }
          if (/\\/api\\/v1\\/threads(\\/\\d+)?$/.test(url) && method !== 'GET') {
            stub.puts.push({method, body: JSON.parse(init.body)});
            stub.notifyPuts();
            return Promise.resolve(new Response(JSON.stringify({
              error: 'revision_conflict', current_revision: 4
            }), {status: 409, headers: {'Content-Type': 'application/json'}}));
          }
          return nativeFetch(input, init);
        };
        """
    )


# AC-201 — a 409 on a chat save shows the exact warning and latches all writes.
def test_browser_conflict_warns_and_stops_further_writes(
    page: Page, app_url: str
) -> None:
    _install_conflict_stub(page)
    page.goto(app_url)
    _rename(page, "stale first")
    puts = _wait(page, "window.__m33Stub.waitForPuts(1)")
    assert len(puts) == 1
    expect(page.get_by_test_id("save-status")).to_have_text(
        "history changed elsewhere — reload required"
    )

    _rename(page, "stale second")
    _wait(page, "window.__m33Stub.waitForTitle('stale second')")
    assert page.evaluate("window.__m33Stub.puts.length") == 1


def _install_reload_stub(page: Page) -> None:
    page.add_init_script(
        """
        const nativeFetch = window.fetch.bind(window);
        const stateKey = '__m33_server_state';
        const putsKey = '__m33_puts';
        const readState = () => JSON.parse(sessionStorage.getItem(stateKey) ||
          '{"revision":3,"title":"Initial"}');
        const readPuts = () => JSON.parse(sessionStorage.getItem(putsKey) || '[]');
        const stub = {putWaiters: []};
        stub.readPuts = readPuts;
        stub.notifyPuts = function() {
          const puts = readPuts();
          const ready = stub.putWaiters.filter(w => puts.length >= w.count);
          stub.putWaiters = stub.putWaiters.filter(w => puts.length < w.count);
          ready.forEach(w => w.resolve(puts));
        };
        stub.waitForPuts = function(count) {
          const puts = readPuts();
          if (puts.length >= count) return Promise.resolve(puts);
          return new Promise(resolve => stub.putWaiters.push({count, resolve}));
        };
        window.__m33Stub = stub;
        window.fetch = function(input, init) {
          const url = typeof input === 'string' ? input : input.url;
          const method = String((init && init.method) || input.method || 'GET').toUpperCase();
          if (url.endsWith('/api/v1/threads') && method === 'GET') {
            const state = readState();
            return Promise.resolve(new Response(JSON.stringify({
              threads: [{id: 1, title: state.title, messages: [], model: 'alpha-model', locked: false, revision: state.revision}],
              revision: 20,
              quarantined: false
            }), {status: 200, headers: {'Content-Type': 'application/json'}}));
          }
          if (/\\/api\\/v1\\/threads\\/\\d+$/.test(url) && method === 'PUT') {
            const body = JSON.parse(init.body);
            const puts = readPuts();
            puts.push(body);
            sessionStorage.setItem(putsKey, JSON.stringify(puts));
            if (puts.length === 1) {
              sessionStorage.setItem(stateKey, JSON.stringify({
                revision: 4, title: 'Current elsewhere'
              }));
              stub.notifyPuts();
              return Promise.resolve(new Response(JSON.stringify({
                error: 'revision_conflict', current_revision: 4
              }), {status: 409, headers: {'Content-Type': 'application/json'}}));
            }
            sessionStorage.setItem(stateKey, JSON.stringify({
              revision: 5, title: body.thread.title
            }));
            stub.notifyPuts();
            return Promise.resolve(new Response(JSON.stringify({
              status: 'ok', revision: 5
            }), {status: 200, headers: {'Content-Type': 'application/json'}}));
          }
          return nativeFetch(input, init);
        };
        """
    )


# AC-148 — reload hydrates authoritative state/revision and unlocks saving.
def test_reload_after_conflict_hydrates_and_allows_a_new_save(
    page: Page, app_url: str
) -> None:
    _install_reload_stub(page)
    page.goto(app_url)
    _rename(page, "stale edit")
    _wait(page, "window.__m33Stub.waitForPuts(1)")
    expect(page.get_by_test_id("save-status")).to_have_text(
        "history changed elsewhere — reload required"
    )

    page.reload()
    expect(page.get_by_test_id("current-thread-title")).to_have_text(
        "Current elsewhere"
    )
    expect(page.get_by_test_id("save-status")).to_have_text("")
    _rename(page, "fresh edit")
    puts = _wait(page, "window.__m33Stub.waitForPuts(2)")
    assert puts[1]["revision"] == 4
    assert puts[1]["thread"]["title"] == "fresh edit"
