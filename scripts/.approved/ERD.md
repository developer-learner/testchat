ERD — testchat (standing architecture)

## Model-selector invariant

**The `#model-select` element MUST NEVER be programmatically disabled by
JavaScript based on a thread's `.locked` field or any per-thread state.** The
only transient disable permitted is the load-in-progress pattern
(`modelSelect.disabled = true` at load start, `modelSelect.disabled = false` at
load completion, unconditionally re-enabled in the `.finally` handler) — a
lifecycle-of-the-load state, not a lifecycle-of-the-thread state. The `.locked`
boolean remains in the persistence schema for backward compatibility but is
never read to disable the selector. Frozen tests assert this
(`test_selector_stays_enabled_across_all_ui_states`,
`test_mid_chat_switch_updates_thread_model_and_routes_next_send`).

## As-built architecture — front end

* **`src/static/chrome.js`** — themes (10 including matrix and phosphor with
  their side effects: matrix-rain canvas start/stop, phosphor titlebar
  `display: flex`), focus mode (fullscreen enter / exit / zen class), settings
  modal (open/save/close, backdrop click), and the generic modal chrome shared
  with the confirm modals owned by other files: backdrop-click dismissal for
  `load-confirm-modal`, `unload-confirm-modal`, `delete-confirm-modal`, and the
  Escape keydown handler that fires each modal's cancel button (or exits zen if
  no modal is open). Exposes `window.Chrome = {}` (self-contained; references
  `window.App.appendBubble` lazily inside `fsDiag`).
* **`src/static/catalog.js`** — model dropdown lifecycle: `fetchModels`
  (parallel `/api/v1/models` + `/api/v1/models/catalog` with LM-Studio-first
  merging), `populateModelOptions` (preserves previous selection, prefers a
  loaded model over the native default, installs a "Select model..."
  placeholder when nothing matches), the eject/unload confirm flow, and the
  `change` handler with pre-change value capture on `focus`/`mousedown` (AC-104
  cancel-reverts) plus the overlapping-load guard (`TC.modelLoading` reverts a
  second pick without opening a modal). Exposes
  `window.Catalog = { fetchModels, refreshModels }`; references
  `window.App.pollStatus` and `window.App.appendBubble` lazily.
* **`src/static/current-chat.js`** — owns the header title for the active
  thread: display + tooltip refresh, inline rename (click → input focused and
  pre-selected; Enter/blur commit; Escape reverts; empty or whitespace-only
  commits revert; newlines collapse to spaces), in-place sidebar-row patching
  on commit, and `commitPending()` which `Threads.switchThread` calls so a
  mid-edit thread switch commits first (AC-118). Exposes
  `window.CurrentChat = { refresh, commitPending }`.
* **`src/static/current-chat.css`** — header-title truncation
  (`max-width: 38%`, ellipsis, native tooltip carries the full string),
  edit-input styling, the `data-active` sidebar highlight (background tint + 3px
  left bar — the non-color signal), and the `select-empty` placeholder voice
  for the model field (muted + italic, matching the message-input placeholder).
* **`src/static/sidebar-resize.js`** — drag handle logic on `#sidebar-resizer`:
  drives a `--sidebar-w` CSS custom property, clamps to [250px, 50vw], persists
  the width to `localStorage` (`tc-sidebar-width`), restores it on load,
  re-clamps on window resize, and resets to the 250px default on double-click.
* **`src/static/sidebar-resize.css`** — re-points `.sidebar`'s fixed width at
  `var(--sidebar-w, 250px)` with `max-width: 50vw`, and styles the 5px grab
  strip (hover/active affordance, drag-time cursor and user-select suppression).
* **`src/static/index.html`** — links both new stylesheets after `style.css`,
  hosts the header title span + rename input (between the model field and the
  settings control), the `sidebar-resizer` divider element, and loads
  `current-chat.js` and `sidebar-resize.js` between `threads.js` and `app.js`
  (load order matters: `app.js` init calls `Threads.renderSidebar()`, which
  calls `CurrentChat.refresh()`).
* **`src/static/threads.js`** — sidebar rows carry `data-active="true|false"`
  and `data-thread-id`; `renderSidebar()` re-syncs the header via
  `CurrentChat.refresh()`; `switchThread()` first calls
  `CurrentChat.commitPending()`; deleting the current thread falls back to the
  **newest** remaining thread; `updateTitle`/`maybeRetitle` store full-length
  titles (cap 120, no baked "..." — AC-127); `renderThreadMessages` builds each
  restored assistant bubble's copy source (`dataset.raw`) with citations
  normalized and `<think>` stripped, matching the live-stream path (AC-128);
  `createThread` prefers a *loaded* model over the dropdown's sticky value and
  leaves the model empty (placeholder) when nothing is loaded. Owns the
  authoritative hydrated revision, the ordered persist queue, and the conflict
  latch (see persistence model below).
* **`src/static/app.js`** — the chat surface: initial-load hydration opens the
  **newest** thread (`threads[]` is oldest-first, so the last element — AC-123)
  and installs both `data.threads` and `data.revision` into the persistence
  owner before rendering or creating state; the submit path guards empty-model
  (guidance bubble `msg-error`, AC-131) and unloaded-model (opens the shared
  load-confirm modal, then auto-resubmits on load success) before any request;
  SSE stream (`token` / `think` / `done` / `error` / `sources` frames), Stop
  button (`AbortController`), bubble helpers, per-message hover actions (copy,
  delete pair), code-block copy, thinking toggle, new-thread button; `pollStatus`
  (5s interval — coupled to `modelSelect` / `sendBtn.disabled` /
  `webToggle.disabled` from `/api/v1/status`); publishes
  `window.App = { appendBubble, pollStatus }` for chrome and catalog to call
  lazily. Load-confirm modal element handles are grabbed here because the
  Send-with-unloaded-model flow and catalog's `change` handler each reassign
  `loadCancel.onclick` / `loadConfirm.onclick` — only one flow runs at a time,
  latest write wins.

## As-built architecture — persistence & revision model

Conflict-safe history persistence keeps the local JSON conversation store
loss-resistant under rapid UI mutations and multiple browser tabs. Each
accepted snapshot carries a real, monotonically increasing persisted revision;
a browser may save only against the revision it hydrated or last received from
an accepted save, and a stale page is rejected rather than overwriting newer
history.

* **`src/services/storage.py`** — public surface: `load_snapshot()` (list-only
  compatibility view for frozen imports), `save_snapshot()`,
  `quarantine_files()`, `load_versioned_snapshot() -> tuple[list[dict], int]`,
  `save_versioned_snapshot(threads, expected_revision) -> int`, and
  `SnapshotConflict.current_revision`. One module-level, non-reentrant lock
  covers read-current / compare / backup / temp-write / atomic-replace /
  revision-advance. A private lock-held helper performs compare / backup /
  replace / revision-advance without acquiring the lock; public
  `save_versioned_snapshot` acquires the lock and calls it; compatibility
  `save_snapshot` acquires the same lock, reads the current generation under it,
  calls the private helper directly, and discards the returned revision (it must
  not call the lock-acquiring public method while holding the lock, and must not
  release the lock between reading and saving). A revision mismatch raises
  `SnapshotConflict` before any directory, temp, backup, or primary write; a
  match always writes `expected + 1` (including an equal PUT and an empty
  DELETE) by same-directory temp replacement. Exactly one `.bak`, rotated by
  `shutil.copy2(primary, bak)` before `os.replace(temp, primary)`; the parent
  directory is created when missing. The generation is an integer, never a
  content hash (an equal snapshot can recur, so a hash would permit ABA). A
  legacy raw-list primary (including a human-restored raw-list `.bak`) reads at
  revision 0; the next accepted write migrates it by ordinary atomic
  replacement and backup rotation. On a JSON-parse failure of the primary, the
  load path quarantines it (rename to `<primary-name>.corrupt-<stamp>` in the
  same directory, bytes preserved exactly) and returns `([], 0)`. Quarantined
  files are never deleted, overwritten, or auto-restored.

  Failure handlers: if `shutil.copy2(primary, bak)` raises `OSError`, warn with
  the primary path, backup path, and exception text, then re-raise that same
  exception; the outer handler removes the prepared temp file and propagates the
  original error, so primary bytes and revision stay fixed and no `.bak`
  appears. If the temp unlink then fails while handling any save error, warn
  with the temp path and cleanup exception but re-raise the ORIGINAL save error —
  cleanup failure never masks the error that began save handling.

* **`src/api/threads.py`** — `ThreadsPayload` carries required `revision: int
  >= 0`; DELETE carries a body model with required `revision: int >= 0`. GET
  performs one revisioned load and returns
  `{"threads": [...], "revision": n, "quarantined": bool}`. PUT calls
  `save_versioned_snapshot(payload.threads, payload.revision)`; DELETE calls it
  with `[]`; both return `{"status":"ok", "revision": n+1}`. `SnapshotConflict`
  maps to HTTP 409 with the exact top-level JSON body
  `{"error":"revision_conflict", "current_revision": n}` (never wrapped in
  FastAPI's `detail`). Validation failures remain 422 and write nothing.

* **`src/static/threads.js` (persistence role)** — owns the authoritative
  hydrated revision, an ordered persist queue, and the conflict latch. Every
  persistence-worthy mutation captures its own complete snapshot at enqueue
  time; at most one PUT runs at a time; the first request uses the hydrated
  revision, and after a 200 the response revision is adopted before the next
  queued snapshot. Mutations are never coalesced or reordered. Ordinary
  network/non-409 failures preserve AC-75/AC-76 (`not saved`) and do not advance
  the revision. A 409 clears pending snapshots, latches the page against every
  later PUT/DELETE, and writes exactly `history changed elsewhere — reload
  required` to `save-status`; only a document reload clears the latch.

Existing quarantine, atomic-replacement, and one-generation-backup behavior
remain in force.

## As-built architecture — model catalog & script-model registry

* **`src/services/models.py`** — LM Studio discovery plus the script-model
  registry. `SCRIPT_MODELS` maps a model id to a launch/probe descriptor
  (`id`, `base_url`, `chat_endpoint`, `ready_url`, `command`,
  `ready_timeout_attr`); a script model is a local OpenAI-compatible server the
  app spawns on demand. Each entry is fed by a per-model constant block read at
  import (`NEMOTRON_*`, `DEEPSEEK_*`), whose `base_url` takes an environment
  override (`NEMOTRON_URL`, `DS4_URL`). `load_script_model` first evicts any
  other resident script model (`_unload_other_script_models`, which iterates
  `SCRIPT_MODELS` to enforce one-resident-at-a-time RAM mutual exclusion), then
  spawns the entry's `command` and waits for its `ready_url` within the entry's
  timeout constant; `unload_script_model` finds the server by the port parsed
  from its `ready_url` (per-process, never by name), SIGINTs then SIGKILLs it,
  and re-probes reachability. `list_models` (LM Studio) and `list_model_catalog`
  (every `SCRIPT_MODELS` entry with its live `loaded` state) feed the two model
  routes.

* **`src/api/models.py`** — projects the registry to the UI. `ModelInfo`
  (`GET /api/v1/models`) and `CatalogEntry` (`GET /api/v1/models/catalog`) each
  pin a closed `Literal` set of `source` strings; `POST
  /api/v1/script-models/{model_id}/load` and `.../unload` route generically by
  id, rejecting an id absent from `SCRIPT_MODELS` with 404. A new registry
  entry therefore surfaces in the catalog and gains load/unload for free — the
  response schema's `source` Literal is the single place that must also learn
  the new id, or the response row fails pydantic validation.

* **Additional model (M34).** `deepseek-v4-flash-0731` joins the registry as a
  third script model: a `DEEPSEEK_0731_*` constant block (base_url default
  `http://127.0.0.1:8005`, env override `DS4_0731_URL`, script path
  `run-server-0731.sh`, readiness-timeout constant) and one `SCRIPT_MODELS`
  entry shaped exactly like `deepseek-v4-flash`, plus the new id appended to
  both `source` Literals in `src/api/models.py`. Normative per-file detail is
  in `ERD-DELTA.md`.

## File inventory

Front-end static: `index.html`, `app.js`, `threads.js`, `current-chat.js`,
`current-chat.css`, `sidebar-resize.js`, `sidebar-resize.css`, `chrome.js`,
`catalog.js`, `markdown.js`, `rain.js`, `style.css`. Back end: `src/api/`
(including `threads.py`) and `src/services/` (including `storage.py`).

`no_edit_files` (also resolved via `--affected`): `markdown.js`, `rain.js`,
`style.css`.

## Oracle mapping

* `tests/test_ui.py` — UI acceptance; element location via `contracts.ui`
  testids only (locked surface includes `sidebar-resizer` and `msg-error`).
  Synchronization via Playwright `expect()` auto-waiting; resize tests use
  `page.mouse` with position math from the handle's own bounding box, no fixed
  sleeps.
* `tests/test_ui_persistence_conflicts.py` — browser-only conflict/latch/reload
  oracles (AC-146..AC-148), synchronizing through explicit Promise barriers
  fired when expected PUTs / title commits are captured — no sleeps, guessed
  microtask turns, or immediate asynchronous request counts.
* `tests/test_persistence_revisions.py` — backend-only revision oracles
  (AC-136..AC-145); imports no Playwright.
* `tests/test_storage_service.py` — storage-service oracles (backup rotation,
  cleanup-failure, quarantine, atomic overwrite).
* `tests/test_threads_api.py`, `tests/test_ui_websearch.py`,
  `tests/test_websearch_api.py` — carried API/feature coverage; direct writers
  obtain and pass the revision.

## Smoke checks

* `chrome.js` — `window.Chrome`, `applyTheme`, `fullscreenEl`, `THEMES` present.
* `catalog.js` — `window.Catalog`, `fetchModels`, `refreshModels`,
  `previousModelValue` present.
* `app.js` — post-split landmarks: `webToggle`, `pendingSources`, the citation
  glyph `【`, `pollStatus`, `queueRender`.
* `current-chat.js` — `CurrentChat` and `commitPending` present.
* `current-chat.css` — `grep -qE "data-active=['\"]true['\"]"` and
  `current-chat-title` present.
* `sidebar-resize.js` — `SidebarResize` and `tc-sidebar-width` present.
* `sidebar-resize.css` — `sidebar-resizer` and `col-resize` present.

## Risk notes

* **Resize geometry.** The drag tests assert against `getBoundingClientRect`
  with a small tolerance; a themed border change that alters layout beyond it
  surfaces as a test failure rather than passing silently — the preferred
  failure direction.
* **Model-endpoint mocks.** AC-130/131/132 tests route both `/api/v1/models`
  and `/api/v1/models/catalog`; if a future milestone renames either route,
  these tests fail loudly at the route mock, which is the correct signal to
  re-true the contracts.

## CEO acceptance (D-44)

Observable without reading code, on any browser — see the PRD "CEO acceptance"
section (current-chat title + highlight + newest-on-refresh; sidebar resize
drag/clamp/persist/reset; no-model placeholder and send guidance; unloaded-pick
confirm-and-revert; clean copy after reload; two-tab conflict latch and reload
recovery).
