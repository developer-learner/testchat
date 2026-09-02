PRD — testchat (standing product spec)

## What testchat is

testchat is a local, single-user web chat application. It talks to
locally-served language models, keeps conversation threads in local JSON on the
server, and runs as one local server process. It has no accounts, no database,
no multi-user tenancy, and no cloud or cross-machine sync.

## How to read this spec

The frozen test suite is the binding acceptance surface (D-54): a behavior is
required if and only if a frozen test pins it. This document narrates the
product and states the acceptance criteria currently in force. Criteria from
earlier milestones that remain live are pinned by their own frozen tests; the
criteria written out below govern the current feature set — current-chat
awareness, free model selection, the composer keyboard behavior (Enter to
send, Shift+Enter for a newline), conflict-safe history persistence,
and the local model catalog.

## Acceptance criteria

**Header title display**

* **AC-111:** THE SYSTEM SHALL display the current thread's title as text in
  the page header, in a region located between the model selector control and
  any header controls to its right. The title SHALL be visible on every page
  load and after every thread switch.

* **AC-112:** WHERE the current thread's title exceeds the width available to
  the header title region, THE SYSTEM SHALL render it truncated (single line,
  no wrap) with the full title reachable via the browser's native tooltip
  (`title` attribute or equivalent hover disclosure). The truncated title
  SHALL NOT cause the header layout to reflow or push other header controls
  out of view.

**Header rename — interaction**

* **AC-113:** WHEN the user clicks the header title, THE SYSTEM SHALL enter
  edit mode: an editable text input replaces (or is layered over) the display
  element, pre-filled with the current title, focused, and with its text
  content selected for immediate overwrite.

* **AC-114:** WHEN the user presses Enter while in header-title edit mode,
  THE SYSTEM SHALL commit the input's current text as the new thread title
  (subject to AC-117), exit edit mode, and persist the rename to the same
  thread record the sidebar rename writes to.

* **AC-115:** WHEN the user presses Escape while in header-title edit mode,
  THE SYSTEM SHALL exit edit mode without changing the stored title, and
  the header SHALL display the title as it was before edit mode was entered.

* **AC-116:** WHEN the user removes focus from the header-title input by any
  means other than Escape (clicking away, tabbing away, switching threads),
  THE SYSTEM SHALL treat it as a commit: apply AC-114 if the input's text is
  non-empty and different from the prior title, otherwise apply AC-115.

* **AC-117:** WHEN a header-title commit is attempted with input text that
  is empty or whitespace-only, THE SYSTEM SHALL discard the input and leave
  the stored title unchanged (same visible effect as AC-115). An empty title
  is never persisted.

* **AC-118:** WHEN the user switches to a different thread while a
  header-title edit is in progress, THE SYSTEM SHALL first commit the
  pending edit under AC-116, then perform the switch. The user's typed text
  SHALL NOT be silently lost.

**Cross-source parity**

* **AC-119:** WHEN a thread is renamed via the sidebar rename affordance
  (`thread-rename-btn` / `thread-rename-input`) AND that thread is the
  current thread, THE SYSTEM SHALL update the header title to the new value
  without requiring a page refresh or a thread switch.

* **AC-120:** WHEN a thread is renamed via the header title AND the sidebar
  is visible, THE SYSTEM SHALL update the sidebar row for that thread to the
  new value without requiring a page refresh or a thread switch. Persistence,
  ordering, and highlighting SHALL be unaffected by which surface the rename
  came from.

**Sidebar highlight**

* **AC-121:** THE SYSTEM SHALL mark exactly one sidebar `thread-item` as the
  current thread, using the DOM attribute `data-active="true"` on that
  element. Every other `thread-item` SHALL either lack the attribute or
  carry `data-active="false"`. The marked row SHALL be visually
  distinguishable from unmarked rows by at least one non-color signal
  (border, background contrast, weight, or indicator glyph) so that the mark
  is discernible for users who cannot perceive color-only differentiation.

* **AC-122:** WHEN the user switches threads, creates a new thread, or
  deletes the currently-active thread, THE SYSTEM SHALL update `data-active`
  such that the newly-current thread carries `data-active="true"` before the
  next paint and no other thread does.

**Load / refresh restoration policy**

* **AC-123:** WHEN the page is loaded or reloaded AND at least one thread
  exists, THE SYSTEM SHALL open the thread that appears first in the sidebar
  ordering (newest first, per the existing
  `test_sidebar_lists_newest_thread_first`). No previously-stored
  "last-opened" or "last-active" thread identifier SHALL override this
  choice.

* **AC-124:** WHEN the page is loaded or reloaded AND zero threads exist,
  THE SYSTEM SHALL create a new empty thread and open it. (The new thread's
  selector is enabled per AC-133; there are no messages, no title beyond
  the default, and no persisted model.)

**Content safety**

* **AC-125:** THE SYSTEM SHALL render thread titles as text, never as HTML,
  in both the header and the sidebar. A title containing HTML markup SHALL
  be visible as literal characters, and SHALL NOT create DOM elements or
  attach event handlers.

* **AC-126:** WHEN a header-title commit contains newline characters, THE
  SYSTEM SHALL strip them (replace with a single space, or drop entirely)
  before persisting. Titles are single-line by construction.

**Title storage**

* **AC-127:** THE SYSTEM SHALL store thread titles at their full length (to a
  storage cap of 120 characters) and SHALL NOT bake a truncation marker into
  the stored string. Visual shortening is render-time only (CSS ellipsis), so
  a wider sidebar reveals more of the same stored title, and the header
  tooltip always carries the full stored text.

**Copy hygiene**

* **AC-128:** THE SYSTEM SHALL provide, for every assistant reply bubble —
  including one restored from persisted history after a reload — a copy
  source that is free of `<think>` reasoning markup, even when the stored
  message content carries such markup inline.

**Sidebar resize**

* **AC-129:** THE SYSTEM SHALL let the user resize the sidebar by dragging
  the divider between the sidebar and the chat panel. The width SHALL clamp
  to no less than 250px and no more than half the viewport width, and the
  chosen width SHALL persist across a reload.

**Model selection guidance**

* **AC-130 (amended — ERD-DELTA v104):** WHEN no model is loaded and the
  active thread has no saved model, THE SYSTEM SHALL show a placeholder
  ("Select model...") in the model field, visually distinct from a real
  selection (muted, italic — the same voice as the message-input
  placeholder), SHALL NOT display an unloaded model as if it were selected,
  and SHALL disable the Send control; any send attempt without a loaded
  model — via the disabled control or via plain Enter (AC-152) — SHALL be
  blocked by the submit guard with the "Pick a model from the dropdown
  before sending." error bubble and SHALL NOT dispatch a message, such that
  no message can be dispatched without a loaded model.
* **AC-131 (retired in v102 — guard-text revival noted in ERD-DELTA
  v104):** the "Pick a model" guidance bubble is no longer the standing
  no-model affordance (the disabled Send control is); it survives only as
  the submit guard's reply to an attempted send — now keyboard-reachable
  via plain Enter (AC-152).
* **AC-132:** WHEN the user picks an unloaded model from the dropdown, THE
  SYSTEM SHALL ask for confirmation before loading; cancelling SHALL revert
  the selection to its prior value and SHALL NOT load anything or send
  anything.

**Free model selection**

* **AC-133:** THE SYSTEM SHALL keep the model selector
  (`data-testid="model-select"`) enabled at all times, on every thread,
  regardless of that thread's message history or persisted `locked`
  field, *such that* `page.get_by_test_id("model-select").is_enabled()`
  returns true after every observable UI state (initial page load,
  send, receive, thread switch, new-chat creation, page reload).

* **AC-134:** WHEN the user switches to a thread, THE SYSTEM SHALL
  restore that thread's most-recently-stored model as the selector's
  current value. IF the stored model is not present in the current
  catalog, THE SYSTEM SHALL fall back to the empty placeholder
  ("Select model...", per AC-130) and SHALL NOT auto-substitute a
  different model.

* **AC-135:** WHEN the user picks a different model from the selector
  on a thread that already has messages, THE SYSTEM SHALL update the
  thread's stored `model` field to the pick *such that*: (a) a
  subsequent send on that thread carries the picked model in its chat
  request payload, and (b) a subsequent page reload opens the thread
  with the picked model shown in the selector.

**Conflict-safe history persistence**

* **AC-136:** WHEN GET `/api/v1/threads` reads no primary snapshot, THE SYSTEM
  SHALL return HTTP 200 with an empty threads array, `revision: 0`, and the
  existing quarantine status.

* **AC-137:** WHEN GET `/api/v1/threads` reads a legacy raw-list primary,
  including a raw-list `.bak` that a human restored to the primary path, THE
  SYSTEM SHALL return every stored thread and message field unchanged with
  `revision: 0`.

* **AC-138:** WHEN a mutation with expected revision 0 is accepted after a
  legacy raw-list primary was read, THE SYSTEM SHALL persist the requested
  threads in the revisioned envelope at revision 1 while retaining the legacy
  primary bytes as the one-generation backup.

* **AC-139:** WHEN PUT `/api/v1/threads` omits its required non-negative
  integer `revision`, THE SYSTEM SHALL return HTTP 422 and create or change no
  persistence artifact.

* **AC-140:** WHEN DELETE `/api/v1/threads` omits its required non-negative
  integer `revision`, THE SYSTEM SHALL return HTTP 422 and create or change no
  persistence artifact, such that the primary snapshot bytes and revision are
  unchanged after the request.

* **AC-141:** WHEN PUT `/api/v1/threads` supplies the current revision, THE
  SYSTEM SHALL replace the snapshot and return a revision exactly one greater
  than the supplied revision, including when the submitted threads equal the
  current threads.

* **AC-142:** WHEN DELETE `/api/v1/threads` supplies the current revision, THE
  SYSTEM SHALL persist an empty threads array and return a revision exactly one
  greater than the supplied revision, including when the snapshot is already
  empty, such that a subsequent GET returns revision n+1 with an empty threads
  array.

* **AC-143:** WHEN PUT `/api/v1/threads` supplies a stale revision, THE SYSTEM
  SHALL return HTTP 409 with exactly `{"error":"revision_conflict",
  "current_revision":<current>}` and leave the primary and one-generation
  backup byte-for-byte unchanged.

* **AC-144:** WHEN DELETE `/api/v1/threads` supplies a stale revision, THE
  SYSTEM SHALL return HTTP 409 with exactly `{"error":"revision_conflict",
  "current_revision":<current>}` and leave the primary and one-generation
  backup byte-for-byte unchanged, such that a subsequent GET still returns the
  last-accepted snapshot and revision.

* **AC-145:** WHEN two process-local mutation requests concurrently supply the
  same current revision, THE SYSTEM SHALL accept exactly one and reject the
  other with HTTP 409 such that the persisted revision and threads identify
  the accepted winner.

* **AC-146:** WHEN one browser page produces multiple persistence-worthy
  mutations before an earlier save completes, THE SYSTEM SHALL issue their
  PUTs serially in mutation order using each accepted response revision as the
  next request precondition.

* **AC-147:** WHEN a browser persist receives HTTP 409, THE SYSTEM SHALL show
  exactly `history changed elsewhere — reload required` in `save-status` and
  issue no further thread mutation request from that page.

* **AC-148:** WHEN a conflict-latched page is reloaded, THE SYSTEM SHALL
  hydrate the server's current threads and revision, clear `save-status`, and
  allow the next user mutation to persist against that hydrated revision
  such that the next save against the hydrated revision is accepted and
  `save-status` shows the empty state.

**Additional local model — deepseek-v4-flash-0731**

* **AC-149:** THE SYSTEM SHALL register a third script model keyed
  `deepseek-v4-flash-0731` in the `SCRIPT_MODELS` registry
  (`src/services/models.py`), alongside the existing `nemotron` and
  `deepseek-v4-flash` entries and in the same entry shape. Its `command` SHALL
  be the single-element list naming the out-of-tree launcher
  `/Users/arc.elixir/dev/ds4/run-server-0731.sh`, and its readiness timeout
  SHALL be a module-level constant named by the entry's `ready_timeout_attr`
  (so a test may monkeypatch it).

* **AC-150:** THE `deepseek-v4-flash-0731` entry's `base_url` SHALL default to
  `http://127.0.0.1:8005` and SHALL be overridable at import time via the
  `DS4_0731_URL` environment variable, matching the `DS4_URL` precedent for
  `deepseek-v4-flash`. Its `chat_endpoint` SHALL end `/v1/chat/completions` and
  its `ready_url` SHALL end `/v1/models`. Registering the entry SHALL leave the
  `nemotron` and `deepseek-v4-flash` entries and all existing model-service
  behavior unchanged.

* **AC-151:** THE model-list response schemas SHALL accept
  `deepseek-v4-flash-0731` as a valid `source` value: constructing
  `ModelInfo(source="deepseek-v4-flash-0731")` and
  `CatalogEntry(source="deepseek-v4-flash-0731", loaded=False)`
  (`src/api/models.py`) SHALL NOT raise a validation error, so that
  `GET /api/v1/models` and `GET /api/v1/models/catalog` can surface the new
  model once its server is discoverable.

**Composer keyboard behavior**

* **AC-152 (amended — ERD-DELTA v104):** WHEN the message input has focus AND
  the user presses the plain Enter key (no Shift/Ctrl/Cmd modifier) AND no IME
  composition is in progress, THE SYSTEM SHALL send the message — the same
  dispatch path the Send button takes — such that pressing plain Enter
  dispatches the message and does not insert a newline.

* **AC-168 (amended — ERD-DELTA v104):** THE dispatch paths SHALL be the Send
  button and plain Enter (AC-152). Shift+Enter SHALL insert a newline at the
  cursor and SHALL NOT send; Ctrl+Enter and Cmd+Enter SHALL NOT send and SHALL
  NOT insert a newline, such that no other keyboard combination produces a
  message dispatch.

* **AC-169 (amended — ERD-DELTA v104):** THE message input's placeholder
  SHALL state "Type a message... (Enter to send, Shift+Enter for newline)"
  — advertising the Enter-to-send shortcut and the Shift+Enter newline
  behavior — and SHALL NOT advertise Ctrl+Enter or Cmd+Enter.

* **AC-153 (retired — superseded by AC-168, ERD-DELTA v102):** Ctrl+Enter /
  Cmd+Enter no longer sends.
* **AC-154 (retired — superseded by AC-168, ERD-DELTA v102):** the empty /
  whitespace-only keyboard guard is gone with the shortcut.
* **AC-155 (retired — superseded by AC-169, ERD-DELTA v102):** the
  placeholder no longer states a shortcut.

**Streaming send control**

* **AC-48 (stop):** WHILE a reply is streaming, THE SYSTEM SHALL present
  the send control as 'Stop'; WHEN the user clicks it after visible text
  has arrived, THE SYSTEM SHALL end the stream, keep the partial reply in
  the thread, and restore the 'Send' control, such that the stream ends
  and no further tokens arrive.

**Data-safety milestone — exact deletion, hydration recovery, schema quarantine**

This milestone closes three paths that can silently discard saved conversation
history. It deliberately changes no chat, model, search, title, or layout
behavior. Completion is user-checkable by deleting one of several chats and
reloading, recovering from a transient history-load failure, and observing a
malformed snapshot preserved under a quarantine name rather than served or
overwritten.

* **AC-156:** WHEN the user confirms deletion of one thread while other
  threads exist, THE SYSTEM SHALL remove exactly the selected thread and
  persist a complete snapshot of every remaining thread through the ordinary
  revisioned replacement path, such that a subsequent page reload displays
  all and only the surviving threads with their titles and messages intact.

* **AC-157:** WHEN the browser performs a per-thread deletion, THE SYSTEM
  SHALL use PUT `/api/v1/threads` with the captured survivor snapshot and
  SHALL NOT use DELETE `/api/v1/threads`; DELETE remains the explicit
  clear-all operation, such that a per-thread deletion cannot persist an
  empty snapshot when survivors remain.

* **AC-158:** WHEN the initial GET `/api/v1/threads` hydration request fails,
  THE SYSTEM SHALL display exactly `history unavailable — retrying` in the
  existing `history-status` element and automatically retry hydration while
  the page remains open; it SHALL NOT create or enqueue a replacement blank
  thread while the persisted revision is unknown.

* **AC-159:** WHEN hydration has failed and a later automatic retry succeeds,
  THE SYSTEM SHALL install the returned threads and revision before accepting
  the next persistence-worthy mutation and clear `history-status`, such that
  the next mutation is accepted against the hydrated revision and a reload
  retains both the hydrated survivors and the new mutation.

* **AC-160:** WHEN a primary snapshot contains valid JSON but any thread or
  message fails the same `ThreadSnapshot` schema used by PUT
  `/api/v1/threads`, THE SYSTEM SHALL move the complete primary bytes to a
  same-directory `<file>.corrupt-<timestamp>` quarantine file and return
  `threads: []`, `revision: 0`, and `quarantined: true`, such that the invalid
  primary is no longer served and its original bytes remain recoverable.

* **AC-166:** WHEN the user saves the system prompt via the settings modal
  and the save request fails, THE SYSTEM SHALL keep the settings modal open
  and display the failure notice `Save failed` in the modal's `settings-status`
  element, such that the user is never left believing the system prompt was
  saved.

* **AC-167:** WHEN the model dropdown is populated from both the models list
  and the script-model catalog, THE SYSTEM SHALL render exactly one option
  per model id, even when the same id is present in both sources, such that
  a loaded script model is never offered twice and the dropdown never
  contains duplicate entries for the same model.

### Router model (dual-path, v107)

* **AC-170:** WHEN `VORTEX_URL` is set AND the router at
  `{VORTEX_URL}/v1/models` answers HTTP 200 with `qwen3.8-27b-8bit` listed in
  its `data`, THE SYSTEM SHALL include the model `qwen3.8-27b-8bit` with
  source `router` in the response of `GET /api/v1/models`, such that the
  router model appears in the model dropdown as a selectable chat model.

* **AC-171:** WHEN the router probe fails (non-200 status or connection
  error) or the router does not list `qwen3.8-27b-8bit`, THE SYSTEM SHALL
  omit the router model from `GET /api/v1/models` and SHALL never include it
  in `GET /api/v1/models/catalog`, such that the dropdown never offers a chat
  that cannot succeed and the script-model load/unload machinery never
  becomes involved with the router model.

* **AC-172:** WHEN a chat request names `qwen3.8-27b-8bit` AND the router
  lists it, THE SYSTEM SHALL stream the reply from
  `{VORTEX_URL}/v1/chat/completions` with the model id passed through
  unchanged, such that the router — not the internal endpoints — answers.

* **AC-173:** WHEN a chat request names the router model id and the router
  does not list it at that moment, THE SYSTEM SHALL reject the request with
  422 before any streaming begins — the same contract as a not-loaded script
  model — such that the request never silently falls through to a different
  backend.

* **AC-174:** WHEN `VORTEX_URL` is not set, THE SYSTEM SHALL expose no router
  model and perform no router probe, such that existing deployments behave
  exactly as before.

### Router recut — full ready set (v115)

The v107 router seams assumed a single hardcoded router model
(`ROUTER_MODEL_ID`). Vortex v26 advertises the full dynamic set of
currently-ready models instead. This recut supersedes the single-model
semantics of AC-170..AC-173 (recorded in ERD-DELTA v115; the historical
blocks above stand as written).

* **AC-175 (supersedes AC-170):** WHEN `VORTEX_URL` is set AND the router
  at `{VORTEX_URL}/v1/models` answers HTTP 200, THE SYSTEM SHALL include
  one entry per model id in the router's `data` — in probe order,
  duplicates removed — each with source `router`, in the response of
  `GET /api/v1/models`, such that the full ready set, not a single
  hardcoded id, appears in the model dropdown as selectable chat models.

* **AC-176 (supersedes AC-171):** WHEN the router probe fails (non-200
  status or connection error) OR the router lists no models, THE SYSTEM
  SHALL omit all router models from `GET /api/v1/models` and SHALL never
  include router models in `GET /api/v1/models/catalog`, such that the
  dropdown never offers a chat that cannot succeed and the script-model
  load/unload machinery never becomes involved with router models.

* **AC-177 (supersedes AC-172):** WHEN a chat request names a model id
  that the router currently lists — any ready Vortex model, not a fixed
  id — AND `VORTEX_URL` is set, THE SYSTEM SHALL stream the reply from
  `{VORTEX_URL}/v1/chat/completions` with the model id passed through
  unchanged, such that the router — not the internal endpoints — answers.

* **AC-178 (supersedes AC-173):** WHEN a chat request names a model id
  that is neither a loaded script model nor in the router's current ready
  set, THE SYSTEM SHALL NOT reject the request pre-stream: the request
  SHALL follow the internal (local) path exactly as before the router
  existed, such that router membership is dynamic and a not-ready model
  is simply not routed to Vortex.

* **AC-179:** WHEN a chat request was routed to the router (its model was
  in the ready set at request time) AND the stream errors without a
  message AND the model is no longer in the router's ready set by the
  time the error is processed (e.g. Vortex answered 404 because the model
  was unloaded between listing and send), THE SYSTEM SHALL emit an SSE
  `error` event whose message is exactly
  `Model {id} is not ready in Vortex. Pick a local model or retry once it is loaded.`
  and the response SHALL remain a 200 SSE stream, such that a mid-flight
  unload surfaces as a not-ready notice with a local fallback offer —
  never as a server error.

* **AC-180:** WHEN a chat request was routed to the router AND the stream
  errors without a message AND the model is still in the router's ready
  set, THE SYSTEM SHALL emit the generic fallback error message (the
  pre-existing behaviour), such that the not-ready notice is specific to
  the model having disappeared from the ready set.

* **AC-181:** THE SYSTEM SHALL NOT define or use a fixed router model id
  constant: `ROUTER_MODEL_ID` is removed from `src/services/models.py`
  and no code path SHALL assume a specific router model id, such that the
  router seam is fully dynamic against Vortex's real v26 surface.

## Out of scope

* **Clear-all redesign or removal.** DELETE `/api/v1/threads` retains its
  revision precondition and empty-snapshot semantics for explicit clear-all
  callers; this milestone only prevents a row delete from invoking it.
* **Automatic merge after hydration failure.** The browser waits for an
  authoritative revision; it does not fabricate a local branch or merge
  unsaved edits into unknown server state.
* **Automatic restore from quarantine or `.bak`.** Invalid snapshots remain
  recoverable by a human but are never silently repaired or restored.

* **Sidebar row auto-scroll on switch.** AC-121 requires the mark to be
  present; it does not require the sidebar to auto-scroll the marked row into
  view when the user switches to a thread off-screen.
* **Undo of an accidental rename commit.** AC-115 provides revert only during
  edit mode. Once committed, the sidebar rename affordance is the recovery
  path; there is no header undo control.
* **Keyboard focus onto the static header title.** AC-113 requires focus after
  a click enters edit mode; it does not require a Tab-navigable landing on the
  static title before edit mode.
* **Custom "empty title" placeholder text.** A thread whose title is
  legitimately empty (created but never messaged) shows whatever the existing
  `thread-item` display shows in that state.
* **Divider double-click reset.** Double-clicking the divider resets the
  sidebar to its default width — shipped, deliberately unpinned (a convenience
  whose exact semantics may change).
* **Load-then-auto-send.** Sending with an unloaded model *selected* offers to
  load it and then dispatches the pending message automatically. The
  confirmation modal contract is pinned (AC-132); the auto-resubmit tail is
  shipped but unpinned.
* **Overlapping-load guard as a formal AC.** The `catalog.js` guard (a second
  model pick while `TC.modelLoading` is true reverts to the prior value and
  opens no second modal) stays in code and is described in the ERD, but is not
  elevated to an AC.
* **Load-failure visibility as a formal AC.** The load path's failure UX
  (`appendBubble(err.message ..., 'error')`) is shipped code, not pinned as a
  criterion.
* **Removal of the `locked` field from the persistence schema.** Deliberately
  kept for backward-compat with existing `data/threads.json` and fixture-based
  tests seeding it; it is never read by the UI.
* **UI signalling that a thread's stored model has changed.** No banner or
  breadcrumb — the dropdown is the signal.
* **Database storage, accounts, authentication, multi-user tenancy, cloud or
  cross-machine sync.**
* **Live cross-tab synchronization, automatic reload, automatic merge,
  conflict-resolution UI, or background retry after a 409.**
* **Draft preservation or partial in-flight reply persistence.**
* **Automatic restore from `.bak` or quarantine.** A human-restored raw-list
  backup is readable under AC-137, but the app never auto-restores.
* **Cross-process locking.** The deployed app remains one local server process.
* **MTPLX or any local coding model as a product chat backend.** MTPLX is an
  engineering-pipeline tool only, never a product chat model.

## Flagged assumptions

* **Sidebar ordering is stable across renames.** AC-119 / AC-120 assume that
  renaming a thread does not change its sidebar position (position is by
  activity or creation time, not by title), matching
  `test_sidebar_lists_newest_thread_first`.
* **Multi-tab semantics.** Highlight and current-thread state are per-tab
  (client state), not shared across tabs. Concurrent tabs are independently
  rendered, but only a mutation based on the current persisted revision is
  accepted — a stale tab is rejected with a conflict (AC-143..AC-147) rather
  than overwriting newer history. Another tab's accepted state becomes visible
  after that tab reloads (AC-148).
* **Rename during message stream.** If the user renames the thread from the
  header while an assistant reply is streaming, the rename commits and the
  streaming reply continues in the same thread record — a pure consequence of
  AC-119 / AC-120 (rename does not touch the message pipeline).

## CEO acceptance — observable without reading code, on any browser

1. Open the app: the header shows the current thread's title; the same thread
   is highlighted in the sidebar; refresh always lands on the newest chat.
2. Drag the divider between sidebar and chat: it follows the pointer, refuses
   to pass the middle of the window, and is still where you left it after a
   refresh. Double-click snaps it back.
3. With no model loaded, open a new chat: the model field reads
   "Select model..." in the same quiet voice as the message box's hint — it
   does not claim a model is active. Hit Send anyway: the app tells you to pick
   a model; nothing is sent.
4. Pick a model that isn't loaded: the app asks before loading. Cancel: your
   selection reverts and nothing loads.
5. Copy an assistant reply after refreshing the page: the clipboard text is
   clean prose — no `<think>` markup.
6. Open the same chat in two tabs. Save a rename in tab A, then rename from
   stale tab B. B shows `history changed elsewhere — reload required`; further
   edits from B do not overwrite A. Reload B: A's accepted state appears, the
   warning clears, and B can save a fresh edit normally.
7. Open the model dropdown: DeepSeek-V4-Flash-0731 appears as a third local
   model beside the others. With its local server running, selecting it loads
   it the same way — and loading it releases whichever other local model was
   resident, since the local models do not run at the same time.
8. In the message box, press Enter: a newline appears at the cursor and
   nothing is sent; Ctrl+Enter and Cmd+Enter are no-ops too. To send, click
   the Send button (the only send path). With no model loaded the Send
   button is disabled. The box's hint text reads "Type a message... (Enter
   for newline)".
9. Create three chats with visibly different titles, delete the middle one,
   and reload: exactly the other two chats return with their original content.
10. During a simulated transient history-load failure, the footer reads
    `history unavailable — retrying`; when the server responds again, the
    warning clears and the next new chat survives reload.
11. Place a syntactically valid snapshot with an invalid message role at the
    data path, then load the page: no malformed thread is rendered, the API
    reports quarantine, and the original bytes remain in a `.corrupt-*` file.
