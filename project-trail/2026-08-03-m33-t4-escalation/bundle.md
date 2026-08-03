## Escalation: caps-exhausted — T4 (spec v77)

### Task entry (tasks/plan.json)
```json
{
  "id": "T4",
  "file": "src/static/app.js",
  "depends_on": [
    "T2",
    "T3"
  ],
  "brief": "During startup GET hydration in src/static/app.js, install BOTH data.threads and data.revision into the threads persistence owner (the hook T3 exposes) before rendering or creating state. A healthy reload starts with empty save-status and an unlatch. If GET is empty, default-thread creation is the first queued save against the returned revision (revision 0). Never infer a revision from content \u2014 always use the data.revision field. Do not restate carried app.js behavior (chat surface, SSE, pollStatus, etc.). Keep the existing init order: hydration happens before renderSidebar/current-chat refresh. Acceptance: the D-64 browser tests pass \u2014 test_browser_serializes_rapid_mutations_in_revision_order, test_browser_conflict_warns_and_stops_further_writes, test_reload_after_conflict_hydrates_and_allows_a_new_save \u2014 and the smoke_check 'revision' grep holds. This task is final and its dependency closure covers every implementation file (T1, T2, T3).",
  "contracts": [
    "ui:save-status",
    "ui:history-status"
  ],
  "tests": [
    "tests/test_ui_persistence_conflicts.py::test_browser_serializes_rapid_mutations_in_revision_order",
    "tests/test_ui_persistence_conflicts.py::test_browser_conflict_warns_and_stops_further_writes",
    "tests/test_ui_persistence_conflicts.py::test_reload_after_conflict_hydrates_and_allows_a_new_save"
  ]
}
```

### Evidence
```
mapped tests failing: tests/test_ui_persistence_conflicts.py::test_browser_serializes_rapid_mutations_in_revision_order[chromium]|tests/test_ui_persistence_conflicts.py::test_reload_after_conflict_hydrates_and_allows_a_new_save[chromium] — tests/test_ui_persistence_conflicts.py::test_browser_serializes_rapid_mutations_in_revision_order[chromium]: ...id("current-thread-title") 14 × locator resolved to <span title="New Chat" id="current-thread-title" class="current-chat-title" data-testid="current-thread-title">New Chat</span> - unexpected value "New Chat" Aria snapshot: - text: New Chat || tests/test_ui_persistence_conflicts.py::test_reload_after_conflict_hydrates_and_allows_a_new_save[chromium]: ...id("current-thread-title") 14 × locator resolved to <span title="New Chat" id="current-thread-title" class="current-chat-title" data-testid="current-thread-title">New Chat</span> - unexpected value "New Chat" Aria snapshot: - text: New Chat
```

### EM diagnosis
(none — caps-exhausted was detected mechanically; no EM consult was
involved because the recorded evidence already identifies the
frozen-spec defect.)

### Frozen artifacts involved
Referenced contract entries:

Frozen test source `tests/test_ui_persistence_conflicts.py`:
```python
"""M33 browser oracle: ordered saves, conflict latch, reload recovery.

Element location uses contracts.ui testids only. Synchronization uses explicit
Promise barriers fired by captured PUTs or committed title mutations; there
are no sleeps, guessed microtask turns, or retry allowances.
"""
from playwright.sync_api import Page, expect


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
          if (!url.endsWith('/api/v1/threads')) return nativeFetch(input, init);
          if (method === 'GET') {
            return Promise.resolve(new Response(JSON.stringify({
              threads: [{id: 1, title: 'Initial', messages: [], model: 'alpha-model', locked: false}],
              revision: 7,
              quarantined: false
            }), {status: 200, headers: {'Content-Type': 'application/json'}}));
          }
          if (method === 'PUT') {
            stub.puts.push(JSON.parse(init.body));
            stub.notifyPuts();
            return new Promise(resolve => stub.resolvers.push(resolve));
          }
          return nativeFetch(input, init);
        };
        """
    )


# AC-146 — rapid mutations wait for the prior accepted revision.
def test_browser_serializes_rapid_mutations_in_revision_order(
    page: Page, app_url: str
) -> None:
    _install_queue_stub(page)
    page.goto(app_url)
    expect(page.get_by_test_id("current-thread-title")).to_have_text("Initial")

    _rename(page, "First mutation")
    _rename(page, "Second mutation")
    puts = page.evaluate("() => window.__m33Stub.waitForPuts(1)")
    assert len(puts) == 1
    assert puts[0]["revision"] == 7
    assert puts[0]["threads"][0]["title"] == "First mutation"

    puts = page.evaluate(
        """() => {
          const barrier = window.__m33Stub.waitForPuts(2);
          window.__m33Stub.respond(0, 200, {status: 'ok', revision: 8});
          return barrier;
        }"""
    )
    assert len(puts) == 2
    assert puts[1]["revision"] == 8
    assert puts[1]["threads"][0]["title"] == "Second mutation"
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
          if (!url.endsWith('/api/v1/threads')) return nativeFetch(input, init);
          if (method === 'GET') {
            return Promise.resolve(new Response(JSON.stringify({
              threads: [{id: 1, title: 'Initial', messages: [], model: 'alpha-model', locked: false}],
              revision: 3,
              quarantined: false
            }), {status: 200, headers: {'Content-Type': 'application/json'}}));
          }
          if (method === 'PUT') {
            stub.puts.push(JSON.parse(init.body));
            stub.notifyPuts();
            return Promise.resolve(new Response(JSON.stringify({
              error: 'revision_conflict', current_revision: 4
            }), {status: 409, headers: {'Content-Type': 'application/json'}}));
          }
          return nativeFetch(input, init);
        };
        """
    )


# AC-147 — 409 shows the exact warning and latches all later writes.
def test_browser_conflict_warns_and_stops_further_writes(
    page: Page, app_url: str
) -> None:
    _install_conflict_stub(page)
    page.goto(app_url)
    _rename(page, "stale first")
    puts = page.evaluate("() => window.__m33Stub.waitForPuts(1)")
    assert len(puts) == 1
    expect(page.get_by_test_id("save-status")).to_have_text(
        "history changed elsewhere — reload required"
    )

    _rename(page, "stale second")
    page.evaluate("() => window.__m33Stub.waitForTitle('stale second')")
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
          if (!url.endsWith('/api/v1/threads')) return nativeFetch(input, init);
          if (method === 'GET') {
            const state = readState();
            return Promise.resolve(new Response(JSON.stringify({
              threads: [{id: 1, title: state.title, messages: [], model: 'alpha-model', locked: false}],
              revision: state.revision,
              quarantined: false
            }), {status: 200, headers: {'Content-Type': 'application/json'}}));
          }
          if (method === 'PUT') {
            const body = JSON.parse(init.body);
            const puts = readPuts();
            puts.push(body);
            sessionStorage.setItem(putsKey, JSON.stringify(puts));
            if (puts.length === 1) {
              sessionStorage.setItem(stateKey, JSON.stringify({
```

