PRD — testchat M29: "unloaded" means unloaded (spec v58)

## Provenance caveat — READ BEFORE APPROVING (INV-1)

This delta was authored by a TPM seat that had **already read `src/`** earlier in
the same session, while occupying the conductor seat during the defect
investigation. Agent-mode TPM is required never to read `src/` (D-39) precisely
so the oracle cannot be derived from the implementation (INV-1). That property
does **not** hold for this delta.

What this does and does not mean:

* The acceptance criteria below are derived from *observed defect behavior*
  (documented in `docs/POSTMORTEM-2026-07-25-unload-spec-lint.md`), not from
  reading implementation internals. They are deliberately written as outcomes
  that any correct implementation must satisfy.
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

Option 2 is the correct one if this delta is treated as precedent. Option 1 is
defensible for a P0 defect fix whose ACs are outcome-shaped.

---

## What changes v57 -> v58

M29 fixes a confirmed P0 defect: **the unload operation reports success without
ever establishing that the model stopped running.** Full evidence, live
reproduction, and the spec lint that found the root cause are in
`docs/POSTMORTEM-2026-07-25-unload-spec-lint.md`.

The defect is not a coding error. It is faithful implementation of AC-95, which
specifies a *mechanism* ("SHALL SIGINT the process ... and return
`{"status":"unloaded"}`") and never an *outcome* ("the model is no longer
running"). The frozen test correspondingly asserts `send_signal` on a mock,
which cannot fail. A lint across 77 acceptance criteria found this flaw confined
entirely to process lifecycle — 5 of 8 process ACs specify mechanisms, while
9 of 9 file-lifecycle ACs specify post-conditions.

This delta restates the process-lifecycle criteria in outcome form and re-cuts
their tests against real subprocesses rather than mocks.

**Why this milestone is cut here (D-46).** The backend correctness defect is P0
and independently CEO-checkable: load a model, restart the app, click Unload,
observe the model actually stop. The UI dead-end defect (a locked thread pinned
to an unloaded model, 26 of 47 threads affected) is real but P1, touches
different files, and needs its own oracle in `tests/test_ui.py`. Bundling them
would double the freeze surface and delay the P0. Defect 2 is specified as M30
below and freezes next.

## Superseded criteria

This delta **retires** the following. They must not survive into v58:

* **AC-95** — replaced by AC-102 and AC-103.
* **AC-96** — replaced by AC-104.
* **AC-7** — replaced by AC-102 (which drops the "tracked subprocess handle"
  precondition entirely; see below).
* **AC-8** — replaced by AC-102's no-op clause.
* **AC-6** — replaced by AC-105.

**Why AC-7's precondition is deleted, not amended.** AC-7 applied only WHEN the
model is reachable AND a tracked handle exists; AC-8 covered the not-reachable
case. The quadrant **reachable but untracked** was covered by neither — and that
quadrant is exactly the state produced by any restart of the server process,
which empties in-memory handles while leaving the spawned model running. The
defect lives in the gap between two criteria that each looked complete. Whether
a handle is tracked is an implementation concern and must not appear in an
acceptance criterion at all; reachability is the only state the user can observe.

## Acceptance criteria

* **AC-102:** WHEN a client requests unload of a registered script model AND
  that model's readiness endpoint is reachable, THE SYSTEM SHALL stop that
  model's server such that, after the response is returned, the model's
  readiness endpoint is no longer reachable — regardless of whether the system
  holds a subprocess handle for it, and regardless of which process spawned it.
  WHEN the readiness endpoint is already unreachable, THE SYSTEM SHALL respond
  `{"status":"unloaded"}` and make no attempt to terminate anything.

* **AC-103:** IF the system cannot bring the model's readiness endpoint to
  unreachable, THEN it SHALL respond `{"status":"error"}` with a `message`
  naming the model, and SHALL NOT respond `{"status":"unloaded"}`. (D-68
  failure-visibility: unload can now fail, so what the user sees on failure is
  specified rather than left to the implementation.)

* **AC-104:** WHEN a client requests load of a registered script model AND any
  other registered script model's readiness endpoint is reachable, THE SYSTEM
  SHALL bring that other model's readiness endpoint to unreachable **before**
  spawning the requested model. IF it cannot, THE SYSTEM SHALL NOT spawn the
  requested model and SHALL respond `{"status":"error"}` with a `message`
  naming the model it could not evict. (Mutual exclusion is a RAM guarantee;
  an unenforceable eviction must fail loudly, never silently proceed to a
  second resident model.)

* **AC-105:** WHEN a spawned script-model server exits before its readiness
  endpoint becomes reachable, THE SYSTEM SHALL respond `{"status":"error"}`
  with a `message` distinguishing that case from the readiness deadline
  elapsing. (Today both report "timeout"; a server that dies on startup — for
  example because its port is already bound — is reported as a 180 s timeout
  after roughly 8 s, which misdirects diagnosis.)

* **AC-106:** WHEN the readiness deadline elapses with the spawned server still
  running, THE SYSTEM SHALL stop that server such that its readiness endpoint is
  unreachable, and respond `{"status":"error"}`. (The AC-6 replacement, in
  outcome form.)

## Out of scope

* The UI dead-end defect (thread pinned to an unloaded model). Specified as M30
  below; not built in this milestone.
* Any change to `/api/v1/models`, `/api/v1/models/catalog`, or chat routing.
  Their contracts are untouched.
* Persisting model state across restarts. The system remains free to hold no
  memory of what it started — AC-102 is deliberately written so that a correct
  implementation may discover a running server rather than remember it.
* The refreeze-time spec lint (proposed gate). Blueprint-side; filed in
  `tasks/BACKLOG.md`.

## Flagged assumptions

1. **Discovery mechanism is the coder's choice.** AC-102 requires reaching a
   server the system did not spawn. It does not say how. `src/api/status.py`
   already performs PID discovery by launch-command basename for RSS reporting,
   so a precedent exists in-tree; port-based discovery is equally acceptable.
   The tests assert only the outcome.
2. **Termination of a process this app does not own may require escalation**
   beyond SIGINT (SIGTERM, then SIGKILL). The grace period stays at 5 s per the
   existing constant. If a server cannot be killed at all — for example it is
   owned by another user — AC-103's error path is the specified outcome, not a
   crash.
3. **The readiness probe is the definition of "running".** A model whose HTTP
   endpoint is unreachable is considered unloaded even if a process lingers.
   This matches how the catalog already reports load state, and keeps the AC
   observable. A lingering process that holds RAM but serves nothing is a
   separate concern, not specified here.
4. **Tests must use real subprocesses for the outcome assertions.** A mocked
   process cannot fail to die, which is precisely how the original defect passed
   a green suite. The re-cut oracle spawns short-lived real servers on
   ephemeral ports and asserts reachability transitions.

---

## M30 — a pinned model must always be loadable (spec'd, not built here)

Recorded now so the criteria are reviewed alongside their root cause; freezes as
its own delta with its own oracle in `tests/test_ui.py`.

**Problem.** A thread stores the model it was last used with. When the app opens
a thread whose stored model is not currently loaded, the selector displays that
model as the current selection. A programmatic selection change fires no
`change` event, and the load-confirm dialog opens only from that event — so no
load path exists. When the thread is additionally locked (which happens after
its first message), the selector is disabled and the user cannot even select
away and back. Sending returns HTTP 422. Confirmed live: 26 of 47 threads in the
CEO's current data are locked and pinned to a script model.

**Spec-integrity finding.** AC-15 ("WHEN the page is refreshed, THE SYSTEM SHALL
unlock the model selector") was the escape hatch that made this unreachable. M8
added persistence, explicitly retired AC-25, and left AC-15 orphaned — and the
M8 replacement test now asserts the selector *is* disabled after reload, which
directly contradicts a live, un-retired criterion. No test pins AC-15.

* **AC-107 (M30):** AC-15 is retired. Refresh restores each thread's stored lock
  state; it does not unlock the selector.
* **AC-108 (M30):** WHERE the active thread's stored model is present in the
  model catalog but not loaded, THE SYSTEM SHALL present a control that starts
  loading that model, reachable in no more than two interactions from the open
  thread, and available even while the thread's model selector is locked.
* **AC-109 (M30):** WHEN that control is activated, THE SYSTEM SHALL show the
  same confirmation the selector's load path shows (naming the model and its RAM
  cost) before spawning anything.
* **AC-110 (M30):** IF the load fails, THEN the user SHALL see the failure in
  the chat error surface and the thread's stored model SHALL be left unchanged
  (D-68 failure visibility).
