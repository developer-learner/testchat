ERD — testchat M31: current-chat awareness (erd_version 64)

## What changes v63 → v64

A behavior delta that adds UI capability. Two inventory files may change (`src/static/index.html`,
`src/static/app.js`). New visual rules are injected by `src/static/app.js`
as a `<style>` element it creates at startup, so `src/static/style.css`
remains in `contracts.no_edit_files` and no new stylesheet file is needed —
a separate CSS file could not be loaded, since `index.html` carries the
only `<link>` and is frequently outside the delta's editable scope.

The delta specifies **16 acceptance criteria** (AC-111..AC-126) covering
header title display, inline rename with full interaction paths, cross-source
rename parity, sidebar highlight of the current thread, load / refresh
selection policy, and content safety. See `PRD.md` for the criteria and for
the INV-1 provenance caveat that must be read before approving this freeze.

## Behavior newly locked

* **AC-111 / AC-112 — header title display.** The current thread's title is
  rendered as text between the model selector and the header's right-side
  controls, single-line, truncated with a native tooltip when it exceeds the
  available width, present on every load and after every thread switch.
  Pinned by
  `test_ui.py::test_current_thread_title_shows_in_header`,
  `test_header_title_updates_when_switching_threads`, and
  `test_long_header_title_truncates_with_full_text_in_tooltip`.

* **AC-113..AC-118 — inline header rename.** Click enters edit mode with the
  input focused and pre-selected; Enter commits, Escape reverts, blur commits
  if the input is non-empty, empty-or-whitespace is never persisted, and
  switching threads mid-edit commits the pending rename before the switch.
  Pinned by
  `test_click_header_title_enters_edit_mode`,
  `test_enter_commits_header_title_edit`,
  `test_escape_reverts_header_title_edit`,
  `test_empty_header_title_commit_reverts_to_prior`,
  and `test_switching_threads_mid_edit_commits_pending_rename`.

* **AC-119 / AC-120 — cross-source parity.** A rename in the sidebar
  updates the header instantly for the current thread; a rename in the
  header updates the sidebar row for that thread instantly. Neither surface
  requires a page refresh to see the other's change. Pinned by
  `test_sidebar_rename_updates_header_immediately` and
  `test_header_rename_updates_sidebar_row_immediately`.

* **AC-121 / AC-122 — sidebar highlight.** Exactly one `thread-item`
  carries `data-active="true"` at any time; every switch, create, or delete
  of the current thread updates that attribute before the next paint. The
  visible mark uses at least one non-color signal. Pinned by
  `test_current_thread_is_highlighted_in_sidebar`,
  `test_highlight_moves_when_switching_threads`, and
  `test_highlight_moves_when_current_thread_deleted`.

* **AC-123 / AC-124 — load / refresh selection policy.** On reload the
  system opens the first-in-sidebar-order thread (matching the existing
  `test_sidebar_lists_newest_thread_first` ordering); zero threads causes
  creation of a new empty thread. Pinned by
  `test_reload_opens_newest_thread` and
  `test_reload_after_current_deleted_opens_newest_remaining`.

* **AC-125 / AC-126 — content safety.** Titles are rendered as text (no
  HTML injection); newlines in a header-title commit are stripped before
  persist. Pinned by `test_title_renders_as_text_not_html` and
  `test_newlines_in_header_title_are_stripped_on_commit`.

## Implementation notes (non-binding — the tests are the contract)

The oracle depends on two new testids being present in the DOM:

* `current-thread-title` — the display element that renders the title text
  (a `<span>`, `<h1>`, or similar). Also serves as the click target that
  enters edit mode per AC-113.
* `current-thread-title-input` — the input element used for the inline
  rename. Present only while in edit mode; can be a text `<input>` or a
  `contenteditable` element.

Both are added to `contracts.ui`; INV-4 rejects any test that references a
testid not in the inventory.

Sidebar highlight uses `data-active="true"` on the existing `thread-item`
testid rather than a new testid, because the highlight is a state on an
existing element and the visual choice (border, background, glyph) is not
prescribed.

Header-title layout and sidebar highlight rules are injected by
`src/static/app.js` into a `<style>` element it creates and appends at
startup. This lets `src/static/style.css` remain in `no_edit_files`
(protecting the 10-theme system from a coder rewrite) while giving the
coder somewhere to put the new visual rules that is guaranteed to load.

The load-order semantics live in `src/static/app.js`. The coder retires
whatever mechanism currently persists a last-opened thread id and
substitutes the "first sidebar row" rule per AC-123.

## File inventory (M31 build) — changed from v60

No inventory changes from v63. Files the delta may or must change:

* **May change:** `src/static/index.html` (header title slot markup),
  `src/static/app.js` (header title wire-up, edit-mode handling, sidebar
  highlight sync, load-selection policy, and the injected `<style>` element
  carrying the highlight and header-title visual rules).
* **Must not change:** every other file in the inventory. `no_edit_files`
  is unchanged from v60; the delta-scoped no-edit inversion (v60 pipeline
  gate) blocks the coder on any file not named by `--affected` for this
  delta.

## Oracle mapping

* `tests/test_ui.py` — full replacement (adds 15 new tests, retains all
  existing 32 tests including the 4 in `test_ui_websearch.py`-adjacent
  scope). Maps to the `src/static/app.js` task by `contracts.entry_points`
  reference; the header markup task (`src/static/index.html`) is covered
  by AC-111's presence assertion; AC-121's non-color-signal requirement is
  covered by the browser oracle's computed-style assertions against the
  styles `src/static/app.js` injects.

**Test-suite properties inherited from D-58:** element location is via
`contracts.ui` testids only (checked at freeze by
`scripts/check-test-surface.py`); synchronization is via Playwright
`expect()` auto-waiting only (no `page.wait_for_timeout`, no `time.sleep`);
zero retries.

## Smoke checks

Unchanged from v63, minus the retired `src/static/current-chat.css` entry.
The injected styles need no smoke check — they are exercised entirely by
the browser oracle's computed-style assertions, and `src/static/app.js`
already carries mapped tests as its acceptance signal.

## Rollback / risk

* Rollback is reverting `src/static/index.html` and `src/static/app.js`,
  then re-freezing v63. No schema changes, no route changes, no
  persistence changes.
* **Risk — sidebar rename regression.** AC-119 / AC-120 require the sidebar
  and header to stay in sync on rename from either surface. If the coder's
  implementation double-fires the update, the sidebar could momentarily
  show a stale value. Mitigation: the paired tests
  (`test_sidebar_rename_updates_header_immediately` and its inverse) assert
  the visible state after the rename settles, using Playwright's auto-wait,
  so a race that eventually settles correctly passes and a race that
  settles wrongly fails.
* **Risk — refresh-restore change is user-visible.** A user who relied on
  the old "refresh returns to the same chat" behavior will see refresh
  land on the newest thread instead. This is the point of AC-123, but it
  is a visible behavior change worth naming at UAT.
* **Risk — highlight visual pass on 10 themes.** The 10-theme system means
  the highlight's non-color signal must be visible under every theme. The
  test asserts the DOM attribute and one computed-style differentiator; a
  theme-specific regression that leaves the mark invisible to the eye but
  present in the DOM would pass the test. Named as a UAT check.
* **Risk — real-browser tests are slower and can flake.** Same class as
  M28's `test_thinking_placeholder_shows_then_clears`. All waits are
  Playwright `expect()` predicates, not fixed sleeps.

## CEO acceptance (D-44)

Observable without reading code, on any browser:

1. Open the app. **Expected:** the current thread's title appears in the
   header between the model selector and the right-side controls; the
   same thread is highlighted in the sidebar list.
2. Click the header title, type a new title, press Enter. **Expected:**
   the header updates immediately and the sidebar row for that thread
   updates to match — with no page refresh.
3. Rename the same thread from the sidebar rename affordance.
   **Expected:** the header title updates to match immediately.
4. Refresh the page. **Expected:** the newest thread opens (top of the
   sidebar list) and is highlighted; no matter which thread was open
   before the refresh, the same top-of-list thread is what appears.
5. Delete the currently-open thread. **Expected:** the newest remaining
   thread opens and is highlighted; the header title updates to match.
