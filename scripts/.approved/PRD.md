PRD — testchat M31: current-chat awareness (spec v64)

## Provenance caveat — READ BEFORE APPROVING (INV-1)

This delta was authored by a TPM seat that had **already read `src/`** earlier in
the same session, while occupying the conductor seat across M29 (v58 → v59) and
the subsequent pipeline-integrity work (v59 → v60). Agent-mode TPM is required
never to read `src/` (D-39) precisely so the oracle cannot be derived from the
implementation (INV-1). That property does **not** hold for this delta.

What this does and does not mean:

* The acceptance criteria below are derived from CEO-stated user problems
  ("current chat is not discoverable in the sidebar list", "refresh takes the
  chat to a specific chat only") and from the M28 lesson that interaction
  criteria must be specified up front, not discovered as live-fixes after
  `[success]`. They are written as outcomes any correct implementation must
  satisfy.
* The tests are nonetheless implementation-informed by construction. Their
  independence is asserted by the author, not guaranteed by structure — which
  is exactly the weaker claim INV-1 exists to avoid relying on.

Recommended dispositions, CEO's call:

1. **Accept with the caveat recorded** (this section stays in the frozen PRD).
   Fastest; the residual risk is a blind spot shared by spec and code.
2. **Re-author the tests from a clean TPM context** (`scripts/tpm-agent.sh` in
   a fresh session, which has never read `src/`), using this PRD as input.
   Restores INV-1 fully. This PRD is contamination-tolerant and can be reused
   as-is.

Precedent: M29 (v58) and v60 both landed under option 1. This is a UI milestone
(M28-shape), where the primary failure mode is not INV-1 — it is unspec'd
interaction paths surfacing as post-`[success]` live-fixes. The spec below
addresses that failure mode directly by exhaustively specifying interaction
ACs; INV-1 contamination is the second-order risk.

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

None. AC-15 was already superseded in v58 by M30's AC-107 (spec'd but not
built). No live criterion is retired here.

**Behavior that is not a frozen AC but changes silently:** whatever mechanism
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
  THE SYSTEM SHALL create a new empty thread and open it. (Consistent with
  existing `test_new_chat_creates_unlocked_empty_thread` semantics for the
  same starting state.)

**Content safety**

* **AC-125:** THE SYSTEM SHALL render thread titles as text, never as HTML,
  in both the header and the sidebar. A title containing HTML markup SHALL
  be visible as literal characters, and SHALL NOT create DOM elements or
  attach event handlers.

* **AC-126:** WHEN a header-title commit contains newline characters, THE
  SYSTEM SHALL strip them (replace with a single space, or drop entirely)
  before persisting. Titles are single-line by construction.

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

## M32 and beyond

Nothing spec'd here. The M30 defect (pinned unloaded model,
AC-107..AC-110) remains reserved from v58 and awaits its own freeze.
