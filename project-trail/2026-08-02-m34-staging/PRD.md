PRD — testchat through M33: current chat, free model selection, conflict-safe persistence (spec v73)

## Provenance caveat — READ BEFORE APPROVING (INV-1)

This version is a **catch-up freeze**: it re-trues the spec to code that
already exists. After the v60–v64 pipeline arc halted five times on spec
defects, the CEO directed a direct hand-build; M31 shipped outside the
pipeline (testchat commit `2ac5827`), along with four further behaviors the
CEO requested live (full-length titles, history-copy hygiene, a resizable
sidebar, model-dropdown guidance).

The INV-1 situation is therefore **inverted, not merely weakened**: the six
new tests in this delta (AC-127..AC-132) were written *after* the
implementation, *by its author*. They are regression pins on as-built
behavior — they cannot serve as an independent oracle for it, and no
disposition short of clean-room re-authoring would make them one. The 15
M31 tests (AC-111..AC-126) predate the implementation (frozen at v63/v64,
untouched here) and retain their original, weaker v64 caveat.

What approving this version means:

1. The inventory and prose stop lying about the tree — the pipeline can plan
   against reality again. This is the load-bearing purpose of v65.
2. The four hand-built behaviors get regression protection with honest
   provenance labels, instead of remaining permanently untested.
3. If independent verification of the hand-built areas is ever wanted, the
   path is a clean-context TPM re-authoring tests from this PRD's AC text
   alone (`scripts/tpm-agent.sh`, fresh session). Not required to proceed.

---

## What changes v66 → v67 (M32)

M32 removes the per-thread model lock (AC-28) so the user can pick any
model on any thread at any point in the conversation.

**Why.** The AC-28 lock forbade changing the model after a thread's
first send. That protection produced a stuck class of thread states
whenever the pinned model became unloaded (app restart, manual eject,
RAM mutual-exclusion eviction): the selector was disabled, the send
button was disabled, and the thread had no in-app recovery path. On
2026-07-25 the live app carried 26 of 47 threads in this state; the
only user workaround was abandoning the thread. The AC-101 backlog
entry proposed a targeted load affordance; CEO instead directed
removing the lock entirely, letting the dropdown become universally
reachable — the existing AC-132 load-then-auto-send flow then covers
the "picked model is unloaded" case naturally.

**What ships.**
* Three new ACs (AC-133..AC-135) pin the free-selection behavior:
  selector always enabled, per-thread sticky on switch, mid-chat pick
  updates the thread's stored model and routes subsequent sends there.
* AC-28 is retired. One frozen test (`test_model_lock_is_per_thread`)
  is removed; three tests are re-staged with their AC-28-era
  disable/enable assertions dropped (`test_new_chat_creates_unlocked_empty_thread`,
  `test_threads_survive_reload`, `test_model_option_labels_never_carry_checkmark`).
* The `locked` boolean stays in the persistence schema (round-tripped
  in `data/threads.json` and in fixture-based tests) but is never read
  by the UI. No data migration; legacy locked threads become usable
  the moment the code ships.
* No contracts.json change (the lock was not represented in any
  `ui`/`routes`/`entry_points`/`schemas`/`errors`/`smoke_checks`
  entry).
* No new files. Coder edits limited to `catalog.js` (drop the
  `modelSelect.disabled = active.locked` assignment) and `threads.js`
  (drop the `lockThread` call and the `ms.disabled = thread.locked`
  on switch).

---

## What changes v64 → v65

* Spec re-true: the ERD now describes the as-built architecture
  (`current-chat.js`/`.css` linked from `index.html` — NOT the v64
  "app.js injects a `<style>` element" design, which was never built).
* Inventory grows by four files: `src/static/current-chat.js`,
  `src/static/current-chat.css`, `src/static/sidebar-resize.js`,
  `src/static/sidebar-resize.css`.
* Six new ACs (AC-127..AC-132) pin the hand-built behaviors; six new tests
  enforce them. All 170 existing tests carry forward byte-identical in
  intent (test_ui.py is restaged with the six appended).
* `contracts.changed_files` (D-86) declares the seven files this version's
  work touched. Nothing here opens new coder scope — the work is built;
  the declaration documents it.
* AC-28 (model locked after first send) is **untouched**. Removing it is a
  live CEO question, deferred to its own version.

---

## What changes v60 → v61

M31 adds three closely related capabilities under one theme — **making the
current chat visible and directly manageable from where the user is looking**:

1. **Top-center title display of the current thread**, between the model
   selector and the header controls to its right.
2. **Inline rename of the current thread from that title**, with parity of
   effect against the existing sidebar rename affordance.
3. **Visual highlight of the current thread in the sidebar**, so the user
   can scroll and identify which sidebar row is open on the right.

And one restoration-policy correction:

4. **On page load or refresh, open the newest thread** (same order the
   sidebar already renders — top row), rather than a stored "last-opened"
   pin. This removes a source of user confusion where refresh appeared to be
   stuck on one specific chat.

**Why one milestone.** All four items concern current-chat awareness — the
user's mental model of "which chat am I on?" Any two of them would leave the
model incomplete: a title without a highlight leaves the sidebar-position
question unanswered; a highlight without a title leaves ellipsis-truncated
thread names still ambiguous; either without the refresh fix means the user
lands on the wrong chat on every reload. Same test surface (`test_ui.py`),
same primary files (`app.js`, `index.html`, one new CSS file), one refreeze.

**Why M28's lesson applies here.** M28 shipped `[success]` and then required
11 post-success live-fixes because interaction ACs (cancel reverts, blur
behavior, race conditions, empty-state handling) were not specified up front.
This milestone is precisely M28-shape — a UI feature with many interaction
paths — so the acceptance criteria below cover **every** interaction path
enumerated during spec, not only the happy paths. If the frozen suite passes,
the milestone is done; there should be no live-fix batch.

---

## Superseded criteria

**v67 (M32):** AC-28 (model locked after first send) is formally
retired. The canonical AC-28 test `test_model_lock_is_per_thread` is
removed. Three tests are re-staged with their AC-28-era
disable/enable assertions dropped; their primary purposes (empty new
thread, reload persistence, no `✓` glyph) survive intact. The
`thread.locked` field stays in the persistence schema for
backward-compat but is never read by the UI.

**v61 (M31):** None. AC-15 was already superseded in v58 by M30's
AC-107 (spec'd but not built). No live criterion was retired.

**Behavior that is not a frozen AC but changes silently (v61):** whatever mechanism
currently causes page refresh to land on a specific stored chat (a stored id
in localStorage, a URL fragment, a persisted "lastActive" field) must no
longer choose the opened thread. AC-123 defines the new selection policy in
outcome terms; the coder retires the old mechanism as part of implementing it.

---

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

---

## v65 catch-up criteria (AC-127..AC-132) — as-built behavior, regression pins

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

---

## v67 (M32) criteria (AC-133..AC-135) — free model selection

**Selector reachability**

* **AC-133:** THE SYSTEM SHALL keep the model selector
  (`data-testid="model-select"`) enabled at all times, on every thread,
  regardless of that thread's message history or persisted `locked`
  field, *such that* `page.get_by_test_id("model-select").is_enabled()`
  returns true after every observable UI state (initial page load,
  send, receive, thread switch, new-chat creation, page reload).

**Per-thread sticky on switch**

* **AC-134:** WHEN the user switches to a thread, THE SYSTEM SHALL
  restore that thread's most-recently-stored model as the selector's
  current value. IF the stored model is not present in the current
  catalog, THE SYSTEM SHALL fall back to the empty placeholder
  ("Select model...", per AC-130) and SHALL NOT auto-substitute a
  different model.

**Mid-chat switch**

* **AC-135:** WHEN the user picks a different model from the selector
  on a thread that already has messages, THE SYSTEM SHALL update the
  thread's stored `model` field to the pick *such that*: (a) a
  subsequent send on that thread carries the picked model in its chat
  request payload, and (b) a subsequent page reload opens the thread
  with the picked model shown in the selector.

---

## Out of scope

* **Sidebar row auto-scroll on switch.** AC-121 requires the mark to be
  present; it does not require the sidebar to auto-scroll the marked row
  into view when the user switches to a thread off-screen. Auto-scroll is a
  defensible enhancement but is deferred so the milestone's test surface
  does not couple to sidebar viewport geometry.
* **Undo of an accidental commit.** AC-115 provides revert only during edit
  mode. Once committed, the sidebar rename affordance is the recovery path;
  no header undo control is required.
* **Keyboard focus onto the static header title.** AC-113 requires focus
  after a click enters edit mode; it does not require a Tab-navigable
  landing on the static title before edit mode. Adding that is a defensible
  accessibility enhancement, deferred.
* **Custom "empty title" placeholder text.** A thread whose title is
  legitimately empty (created but never messaged) shows whatever the
  existing `thread-item` display already shows in that state; this
  milestone does not redefine that behavior.
* **(v65) Divider double-click reset.** Double-clicking the divider resets
  the sidebar to its default width. Shipped, deliberately unpinned — a
  convenience whose exact semantics may change.
* **(v65) Load-then-auto-send.** Sending with an unloaded model *selected*
  offers to load it and then dispatches the pending message automatically.
  The confirmation modal contract is pinned (AC-132); the auto-resubmit
  tail is shipped but unpinned, pending a mock-load harness that doesn't
  spawn a real model process inside the fixture.
* **(v67) Overlapping-load guard as a formal AC.** The existing guard
  in `catalog.js` (a second model pick made while `TC.modelLoading` is
  true reverts to the prior value and opens no second modal) stays in
  code and is described as prose in the ERD, but is not elevated to
  an AC — a Playwright test for it would need to route the
  script-model load endpoint to hang, and the guard has never
  regressed. Regression protection stays; formal spec deferred.
* **(v67) Load-failure visibility as a new AC.** The load path's
  failure UX (`appendBubble(err.message ..., 'error')` in the
  catalog's `.catch`) is shipped code, unchanged by M32, and now
  exercisable from more thread states. Elevating it into a pinned AC
  is a defensible separate milestone; this one does not open that
  scope.
* **(v67) Removal of the `locked` field from the persistence schema.**
  Deliberately kept — backward-compat with existing `data/threads.json`
  and with fixture-based tests seeding it. Cleaning the schema is a
  defensible follow-up when the tolerated read-only tail is judged
  closable.
* **(v67) UI signalling that a thread's stored model has changed.** No
  banner or breadcrumb. The dropdown IS the signal.

---

## Flagged assumptions

* **Sidebar ordering is stable across renames.** AC-119 / AC-120 assume
  that renaming a thread does not change its sidebar position (position is
  by activity or creation time, not by title). This matches existing
  `test_sidebar_lists_newest_thread_first`. If ordering ever becomes
  title-driven, AC-121's highlight semantics still hold but the visible
  position of the highlighted row would move on rename — a UX regression
  this spec does not prevent.
* **Multi-tab semantics.** Highlight and current-thread state are per-tab
  (client state), not shared across tabs of the same user. Renames persist
  server-side, so a rename in tab A becomes visible in tab B on tab B's
  next thread-list refresh. This is inherited behavior, not new.
* **Rename during message stream.** If the user sends a message and, while
  the assistant reply is streaming, renames the thread from the header, the
  rename SHALL commit and the streaming reply SHALL continue in the same
  thread record. No AC pins this because it is a pure consequence of
  AC-119 / AC-120 (rename does not touch the message pipeline). Called out
  only so a reviewer knows it was considered.

---

## M33 and beyond

M30's reserved AC-107..AC-110 (targeted load affordance for pinned
unloaded models) are formally superseded by M32's AC-133..AC-135 — the
lock removal dissolves the defect class those ACs were reserved for.

---

## What changes v71 → v72 (M33)

M33 makes the existing local JSON conversation history loss-resistant under
rapid UI mutations and multiple browser tabs. Each accepted snapshot has a
real monotonically increasing persisted revision. A browser may save only
against the revision it hydrated or most recently received from an accepted
save; stale pages are rejected instead of overwriting newer history.

**Formal supersession:** M8 flagged assumption A15 (concurrent tabs are
last-write-wins) is retired. Concurrent tabs remain independently rendered,
but only a mutation based on the current persisted revision may be accepted.
The v71 multi-tab assumption above remains true only for visibility: another
tab's accepted state becomes visible after reload; it does not authorize a
stale overwrite.

All other v71 text above is carried forward verbatim and remains in force.
No existing numbered acceptance criterion is retired or weakened by M33.

**Why one milestone.** The persisted generation, API precondition, storage
lock, ordered browser queue, conflict message, and reload recovery are one
indivisible user promise: an older full snapshot cannot erase a newer
accepted one. Shipping only a subset would either leave the race open or
strand the user without a recovery path.

### M33 acceptance criteria (EARS notation)

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
  persistence artifact.

* **AC-141:** WHEN PUT `/api/v1/threads` supplies the current revision, THE
  SYSTEM SHALL replace the snapshot and return a revision exactly one greater
  than the supplied revision, including when the submitted threads equal the
  current threads.

* **AC-142:** WHEN DELETE `/api/v1/threads` supplies the current revision, THE
  SYSTEM SHALL persist an empty threads array and return a revision exactly one
  greater than the supplied revision, including when the snapshot is already
  empty.

* **AC-143:** WHEN PUT `/api/v1/threads` supplies a stale revision, THE SYSTEM
  SHALL return HTTP 409 with exactly `{"error":"revision_conflict",
  "current_revision":<current>}` and leave the primary and one-generation
  backup byte-for-byte unchanged.

* **AC-144:** WHEN DELETE `/api/v1/threads` supplies a stale revision, THE
  SYSTEM SHALL return HTTP 409 with exactly `{"error":"revision_conflict",
  "current_revision":<current>}` and leave the primary and one-generation
  backup byte-for-byte unchanged.

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
  allow the next user mutation to persist against that hydrated revision.

### M33 contract changes

GET `/api/v1/threads` adds `revision`. PUT's existing payload adds required
`revision`. DELETE requires a body containing `revision`. Every accepted PUT
or DELETE returns `{"status":"ok","revision":<new>}`. Stale mutations use
the exact top-level 409 body in AC-143/AC-144; it must not be wrapped in a
framework `detail` key.

The current on-disk document becomes
`{"revision": <integer>, "threads": [...]}`. Legacy raw-list primaries read
as revision 0; the next accepted write migrates by ordinary atomic replacement
and backup rotation. The generation is an integer, never a content hash (an
equal snapshot can recur, so a hash permits ABA). Compare, backup rotation,
temp write, atomic replace, and revision advance occur under one process-local
lock. `load_snapshot()` remains a thread-list compatibility view for frozen
imports. Existing quarantine, atomic replacement, and one-generation backup
behavior remain in force.

**v73 lock correction.** The one lock is non-reentrant. A private lock-held
save helper performs compare / backup / replace / revision advance without
acquiring the lock itself. Public `save_versioned_snapshot` acquires the lock
and calls that helper. Compatibility `save_snapshot` separately acquires the
same lock, reads the current generation under that lock, calls the private
helper directly, and discards its returned revision. It SHALL NOT call the
lock-acquiring public `save_versioned_snapshot` while holding the lock, and it
SHALL NOT release the lock between reading and saving.

The browser owns one hydrated revision, snapshots each mutation when enqueued,
and runs at most one persist request at a time. A 200 response advances the
local revision before the next queued request. Ordinary network/non-409
failures retain AC-75/AC-76 behavior. A 409 clears queued snapshots and latches
all later writes until document reload.

### M33 failure-visibility maintenance rider

**v73 corrects the v72 handler location.** The reported unhandled
`except OSError: pass` surrounds backup rotation, specifically
`shutil.copy2(primary, backup)`; it is not the later temp-unlink handler.
WHEN that backup copy raises `OSError`, the storage service SHALL log a warning
that includes the primary path, backup path, and exception, then re-raise that
same backup error. The outer save-failure path removes the prepared temp file
and propagates the original backup error, so the primary bytes/revision are
not replaced or advanced and AC-75 exposes the failure instead of reporting a
save.

The later temp-unlink failure path is also explicit: IF removing the temp file
while handling any primary save error raises `OSError`, the service SHALL log
the temp path and cleanup exception but preserve and re-raise the ORIGINAL
primary save error after the cleanup attempt. Cleanup failure must never mask
the error that caused save handling to begin.

No new numbered criterion is added. These are missing failure-path oracles for
existing AC-82 (backup rotation is part of a successful save) and AC-75 (a
failed save propagates to the already-specified visible `not saved` state),
not a new user capability.

### M33 out of scope

* Database storage, accounts, authentication, multi-user tenancy, cloud or
  cross-machine sync.
* Live cross-tab synchronization, automatic reload, automatic merge, conflict
  resolution UI, or background retry after a 409.
* Draft preservation or new partial in-flight reply persistence.
* Automatic restore from `.bak` or quarantine; a human-restored raw-list
  backup is readable under AC-137.
* Cross-process locking; the deployed app remains one local server process.
* MTPLX or any local coding model as a product chat backend. MTPLX is an
  engineering-pipeline tool only.

### M33 CEO demo

Open the same chat in two tabs. Save a rename in tab A, then rename from stale
tab B. B shows `history changed elsewhere — reload required`; further edits
from B do not overwrite A. Reload B: A's accepted state appears, the warning
clears, and B can save a fresh edit normally.

## What changes v73 → v74 (M34)

M34 adds `deepseek-v4-flash-0731` to the script-model registry so the user
can load it, chat with it, and unload it through the existing catalog / load
/ unload / eject UI, alongside `nemotron` and `deepseek-v4-flash`.

**Why.** DeepSeek published V4-Flash-0731 on 2026-07-31 with substantial
agentic and coding-benchmark gains over the V4-Flash preview shipped in the
current registry. Both models are served by antirez's `ds4-server` runtime
already used for the existing preview entry; the addition is registry-only
and reuses the whole script-model mechanism (RAM mutual exclusion, per-id
load/unload, catalog projection, chat routing).

**Scope.** Pure catalog addition. No new routes, no new schemas, no new UI
elements, no changes to the load/unload contract, no changes to any
existing model's behavior.

### M34 acceptance criteria (EARS notation)

* **AC-149:** THE SCRIPT-MODEL registry SHALL include the entry keyed
  `deepseek-v4-flash-0731` alongside the pre-existing `nemotron` and
  `deepseek-v4-flash` entries. Its `command` SHALL be the single-element list
  `["/Users/arc.elixir/dev/ds4/run-server-0731.sh"]`.

* **AC-150:** THE `deepseek-v4-flash-0731` entry SHALL have `chat_endpoint`
  ending with `/v1/chat/completions` and `ready_url` ending with `/v1/models`.
  Its `base_url` SHALL default to `http://127.0.0.1:8005` and SHALL be
  overridable via the `DS4_0731_URL` environment variable read at module
  import (matching the `DS4_URL` precedent for `deepseek-v4-flash`).

* **AC-151:** WHEN a client calls `GET /api/v1/models/catalog`, THE response
  body's `models` array SHALL include an entry with `id` and `source` both
  equal to `deepseek-v4-flash-0731` and `loaded` reflecting whether the
  registered `ready_url` currently returns HTTP 200.

* **AC-152:** THE `ModelInfo.source` and `CatalogEntry.source` Literal unions
  SHALL accept the value `"deepseek-v4-flash-0731"` such that
  `GET /api/v1/models` and `GET /api/v1/models/catalog` do not raise a
  pydantic ValidationError when the new source is present in a response row.

* **AC-153:** WHEN a client calls `POST /api/v1/script-models/deepseek-v4-flash-0731/load`,
  THE system SHALL first evict any other script model whose process handle
  is set or whose `ready_url` currently returns HTTP 200 (existing RAM mutual
  exclusion path), THEN spawn the entry's `command`, THEN wait for the
  entry's `ready_url` to return HTTP 200 within
  `DEEPSEEK_0731_READY_TIMEOUT_SECONDS`, and SHALL return 200 body
  `{"status":"loaded"}` on ready or 503 body `{"status":"error", "message": ...}`
  on child-exit or deadline (matching the existing script-model contract).

* **AC-154:** WHEN a client calls `POST /api/v1/script-models/deepseek-v4-flash-0731/unload`,
  THE system SHALL SIGINT (grace) then SIGKILL the entry's process (tracked
  handle first, else discovered by the entry's `ready_url` port),
  re-probe the entry's `ready_url`, and SHALL return 200 body
  `{"status":"unloaded"}` iff the re-probe now fails, else 503 body
  `{"status":"error"}` — matching AC-95's existing contract for
  `deepseek-v4-flash` and `nemotron`.

### M34 contract changes

`SCRIPT_MODELS` in `src/services/models.py` gains one entry. The module
grows five new module-level constants derived from the pre-existing
`DEEPSEEK_*` pattern: `DEEPSEEK_0731_BASE_URL`, `DEEPSEEK_0731_CHAT_ENDPOINT`,
`DEEPSEEK_0731_READY_URL`, `DEEPSEEK_0731_SCRIPT_PATH`, and
`DEEPSEEK_0731_READY_TIMEOUT_SECONDS` (default 300). All existing constants,
the `nemotron` entry, and the `deepseek-v4-flash` entry are unchanged.

`ModelInfo.source` and `CatalogEntry.source` in `src/api/models.py` each
gain `"deepseek-v4-flash-0731"` as an additional Literal member. All other
Literal members and all other schemas are unchanged.

The `deepseek-v4-flash-0731` server binary lives out-of-tree at
`/Users/arc.elixir/dev/ds4/run-server-0731.sh`; it is host-owned ops config
and is not part of the pipeline's file inventory. The registry entry names
it by absolute path exactly as the existing `deepseek-v4-flash` entry names
`run-server.sh`.

### M34 out of scope

* Any change to `nemotron` or `deepseek-v4-flash` behavior, ports, or
  timeouts.
* Any change to the load/unload/catalog HTTP surface beyond the new id
  being valid.
* Any UI-side change (the selector already renders the catalog as-served).
* Removing or symlink-swapping the `deepseek-v4-flash` preview (whose gguf
  file is separately missing on host — that is a host-config issue outside
  this spec).
