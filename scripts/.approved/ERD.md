ERD — testchat M31 as built + hand-build coverage (erd_version 65)

## What changes v64 → v65

A catch-up re-true, not a build delta. M31 was hand-built outside the
pipeline (commit `2ac5827` + `57b40b8`) after the v60–v64 arc; this version
makes the frozen spec describe the tree as it actually is, adds the four
new files to the inventory, and pins six hand-built behaviors
(AC-127..AC-132) with regression tests. See the PRD provenance caveat —
the new tests postdate the implementation and share its author.

**The v64 design this supersedes was never built:** v64 specified that
`src/static/app.js` would inject a `<style>` element at startup because a
separate stylesheet "could not be loaded". The hand-build did the simpler
correct thing v64 talked itself out of: it edited `index.html`, which was
always editable (only `markdown.js`, `rain.js`, `style.css` are
`no_edit_files` — "outside the delta" was a scoping artifact, not a
property of the file).

## As-built architecture

* **`src/static/current-chat.js`** (new) — owns the header title for the
  active thread: display + tooltip refresh, inline rename (click → input
  focused and pre-selected; Enter/blur commit; Escape reverts; empty or
  whitespace-only commits revert; newlines collapse to spaces), in-place
  sidebar-row patching on commit, and `commitPending()` which
  `Threads.switchThread` calls so a mid-edit thread switch commits first
  (AC-118). Exposes `window.CurrentChat = { refresh, commitPending }`.
* **`src/static/current-chat.css`** (new) — header-title truncation
  (`max-width: 38%`, ellipsis, native tooltip carries the full string),
  edit-input styling, the `data-active` sidebar highlight (background tint
  + 3px left bar — the non-color signal), and the `select-empty`
  placeholder voice for the model field (muted + italic, matching the
  message-input placeholder).
* **`src/static/sidebar-resize.js`** (new) — drag handle logic on
  `#sidebar-resizer`: drives a `--sidebar-w` CSS custom property, clamps to
  [250px, 50vw], persists the width to `localStorage`
  (`tc-sidebar-width`), restores it on load, re-clamps on window resize,
  and resets to the 250px default on double-click.
* **`src/static/sidebar-resize.css`** (new) — re-points `.sidebar`'s fixed
  width at `var(--sidebar-w, 250px)` with `max-width: 50vw`, and styles the
  5px grab strip (hover/active affordance, drag-time cursor and
  user-select suppression).
* **`src/static/index.html`** — links both new stylesheets after
  `style.css`, hosts the header title span + rename input (between the
  model field and the settings control), the `sidebar-resizer` divider
  element, and loads `current-chat.js` and `sidebar-resize.js` between
  `threads.js` and `app.js` (load order matters: `app.js` init calls
  `Threads.renderSidebar()`, which calls `CurrentChat.refresh()`).
* **`src/static/threads.js`** — sidebar rows carry
  `data-active="true|false"` and `data-thread-id`; `renderSidebar()`
  re-syncs the header via `CurrentChat.refresh()`; `switchThread()` first
  calls `CurrentChat.commitPending()`; deleting the current thread falls
  back to the **newest** remaining thread; `updateTitle`/`maybeRetitle`
  store full-length titles (cap 120, no baked "..." — AC-127);
  `renderThreadMessages` builds each restored assistant bubble's copy
  source (`dataset.raw`) with citations normalized and `<think>` stripped,
  matching the live-stream path (AC-128); `createThread` prefers a
  *loaded* model over the dropdown's sticky value and leaves the model
  empty (placeholder) when nothing is loaded.
* **`src/static/app.js`** — initial-load hydration opens the **newest**
  thread (`threads[]` is oldest-first, so the last element — AC-123);
  `populateModelOptions` prefers a loaded model when nothing matches,
  else prepends a disabled hidden "Select model..." option and tags the
  field `select-empty` (AC-130); the submit path guards empty-model
  (guidance bubble `msg-error`, AC-131) and unloaded-model (load-confirm
  modal, then auto-resubmit on success) before any request; error bubbles
  carry `data-testid="msg-error"`.

## Behavior locked by this version (beyond the v64 set)

* **AC-127 — full-length title storage.** Pinned by
  `test_thread_title_stores_full_text_beyond_thirty_chars`.
* **AC-128 — history-copy hygiene.** Pinned by
  `test_reply_copy_source_strips_think_after_reload` (the fixture stream
  deliberately carries inline `<think>…</think>`, so the stored message
  contains markup the copy source must not).
* **AC-129 — sidebar resize: drag, clamp, persist.** Pinned by
  `test_sidebar_divider_drags_and_clamps` and
  `test_sidebar_width_persists_across_reload`.
* **AC-130 / AC-131 — placeholder + send guidance.** Pinned by
  `test_no_loaded_model_shows_placeholder_and_send_guides` (routes both
  model endpoints to a nothing-loaded state).
* **AC-132 — unloaded-pick confirmation contract.** Pinned by
  `test_unloaded_model_pick_asks_and_cancel_reverts`.

The 15 M31 tests (AC-111..AC-126) carry forward untouched and now pass
against the as-built code.

## File inventory

16 files. Added this version (all new, all shipped):

* `src/static/current-chat.js`
* `src/static/current-chat.css`
* `src/static/sidebar-resize.js`
* `src/static/sidebar-resize.css`

`no_edit_files` unchanged: `markdown.js`, `rain.js`, `style.css`.

`contracts.changed_files` (D-86) declares the seven files the hand-build
touched: the four above plus `app.js`, `threads.js`, `index.html`. This
documents provenance; no coder run is pending against this version.

## Oracle mapping

* `tests/test_ui.py` — full replacement: all previous tests byte-identical,
  six appended (mapping above). Element location via `contracts.ui` testids
  only; two additions to the locked surface: `sidebar-resizer` (the
  divider) and `msg-error` (guidance/error bubbles). Synchronization via
  Playwright `expect()` auto-waiting; the resize tests use `page.mouse`
  with position math from the handle's own bounding box, no fixed sleeps.

## Smoke checks

The four new files get presence checks, quote-agnostic per the v61 lesson
(single- and double-quoted forms both match):

* `current-chat.js` — `CurrentChat` and `commitPending` present.
* `current-chat.css` — `grep -qE "data-active=['\"]true['\"]"` and
  `current-chat-title` present.
* `sidebar-resize.js` — `SidebarResize` and `tc-sidebar-width` present.
* `sidebar-resize.css` — `sidebar-resizer` and `col-resize` present.

Existing entries unchanged.

## Rollback / risk

* Rollback is `git revert` of `2ac5827` + `57b40b8` and a re-freeze to the
  v64 spec — no schema, route, or persistence changes anywhere in the arc.
* **Risk — regression pins, not an oracle.** The six new tests verify the
  implementation against itself at freeze time. They will catch future
  regressions; they cannot catch present defects. Named in the PRD
  provenance caveat; accepted by approving this freeze.
* **Risk — resize geometry.** The drag tests assert against
  `getBoundingClientRect` with a ±6px tolerance; a themed border change
  that alters layout by more than that will surface as a test failure
  rather than silently passing (preferred failure direction).
* **Risk — model-endpoint mocks.** AC-130/131/132 tests route both
  `/api/v1/models` and `/api/v1/models/catalog`; if a future milestone
  renames either route, these tests fail loudly at the route mock, which
  is the correct signal to re-true the contracts.

## CEO acceptance (D-44)

Observable without reading code, on any browser:

1. Open the app: header shows the current thread's title; the same thread
   is highlighted in the sidebar; refresh always lands on the newest chat.
2. Drag the divider between sidebar and chat: it follows the pointer,
   refuses to pass the middle of the window, and is still where you left
   it after a refresh. Double-click snaps it back.
3. With no model loaded, open a new chat: the model field reads
   "Select model..." in the same quiet voice as the message box's hint —
   it does not claim a model is active. Hit Send anyway: the app tells you
   to pick a model; nothing is sent.
4. Pick a model that isn't loaded: the app asks before loading. Cancel:
   your selection reverts and nothing loads.
5. Copy an assistant reply after refreshing the page: the clipboard text
   is clean prose — no `<think>` markup.
