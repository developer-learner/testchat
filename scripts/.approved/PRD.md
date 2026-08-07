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
awareness, free model selection, the composer keyboard shortcuts (Enter for a
newline, Ctrl+Enter / Cmd+Enter to send), conflict-safe history persistence,
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

* **AC-130:** WHEN no model is loaded and the active thread has no saved
  model, THE SYSTEM SHALL show a placeholder ("Select model...") in the
  model field, visually distinct from a real selection (muted, italic — the
  same voice as the message-input placeholder), and SHALL NOT display an
  unloaded model as if it were selected.
* **AC-131:** WHEN the user sends a message with no model selected, THE
  SYSTEM SHALL show guidance naming the fix (pick a model) instead of
  surfacing a raw backend error, and SHALL NOT dispatch the chat request.
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

* **AC-152:** WHEN the message input has focus AND the user presses the
  Enter key AND no IME composition is in progress, THE SYSTEM SHALL insert
  a newline at the cursor position and SHALL NOT send the message.

* **AC-153:** WHEN the message input has focus AND the user presses
  Ctrl+Enter (or Cmd+Enter on macOS) AND no IME composition is in progress
  AND the input contains non-whitespace text, THE SYSTEM SHALL send the
  message through the same path as the send button.

* **AC-154:** WHEN the user presses Ctrl+Enter (or Cmd+Enter on macOS)
  while the message input is empty or whitespace-only, THE SYSTEM SHALL
  send nothing and SHALL leave the input unchanged.

* **AC-155:** THE message input's placeholder SHALL state the keyboard
  shortcuts: "Ctrl+Enter to send, Enter for newline".

## Out of scope

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
   nothing is sent. Press Ctrl+Enter (Cmd+Enter on macOS): the message sends.
   With the box empty or whitespace-only, Ctrl+Enter sends nothing and the
   input is unchanged. The box's hint text reads "Ctrl+Enter to send, Enter
   for newline".
