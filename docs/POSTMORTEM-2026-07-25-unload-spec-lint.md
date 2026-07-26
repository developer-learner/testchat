# Postmortem — 2026-07-25: three defects, one spec-authoring root cause

**Status:** defects confirmed by live reproduction; docs defect fixed in this
commit; the two code defects require a TPM spec delta (see §6).
**Tree audited:** `c4710cc` (byte-identical to `1204546`; verified `git diff` empty).
**Author:** conductor seat. `src/` and `tests/` were not touched — outside the
conductor lane (D-40). This document and the README/CLAUDE.md port fix are.

---

## 1. What was claimed, and what is true

Three claims were filed for independent review. All three are real. Two were
understated by the original report; one carried two factual overreaches.

| # | Claim | Verdict | Correction to the original report |
|---|-------|---------|-----------------------------------|
| 1 | `unload_script_model` returns `"unloaded"` without verifying the process died | **Confirmed** | Understated. The RAM mutual-exclusion guarantee also silently fails. |
| 2 | A thread pinned to an unloaded model has no way to load it | **Confirmed** | Understated. On a `locked` thread the selector is *disabled*, so the report's stated workaround does not exist. |
| 3 | The README's default run command collides with DeepSeek on port 8000 | **Confirmed** | Two overreaches: fails in **8 s**, not 180 s; the "silent hijack" case is unreachable from the documented command. |

None of the three were artifacts of the 2026-07-25 session's port confusion.
Claim 1's mechanism is in code unchanged since 2026-07-19 and was reproduced
from a clean process; Claim 2's trigger lives in `data/threads.json` and is
live; Claim 3 is a mismatch between committed files.

---

## 2. Defect 1 — "unloaded" does not mean unloaded

Process handles live in a module-level dict (`src/services/models.py:50`).
Any restart of the uvicorn worker empties it. `unload_script_model` returns
`{'status': 'unloaded'}` whether or not it had a handle to kill.

**Reproduced end-to-end** (fresh app process + a live server on `127.0.0.1:8000`):

```
POST /api/v1/script-models/deepseek-v4-flash/unload
  → {"status":"unloaded"}  HTTP 200
  → process still alive, reparented to PPID 1
  → still LISTEN on 127.0.0.1:8000
  → GET /api/v1/models/catalog still reports "loaded": true
```

**The `--reload` path was verified directly**, closing the original report's
untested inference. uvicorn 0.49.0 `supervisors/basereload.py:96` calls
`self.process.terminate()` — the worker PID only, never a process group.
Observed: a file save killed worker 95504; its `Popen` child 95505 survived
with `PPID=1`. The worker is a `multiprocessing` **spawn** child, so the new
worker starts with an empty handle dict. Both halves of the mechanism confirmed.
No `atexit`, `lifespan`, or `on_event` hook exists anywhere in `src/`.

**Severity is higher than "a wrong status string."** The mutual-exclusion
guarantee at `models.py:104` — *"script models are RAM-heavy, only one runs at
a time"* — silently fails. Demonstrated: with a live-but-untracked DeepSeek,
`load_script_model('nemotron')` called unload (got `unloaded`, killed nothing)
and **then spawned nemotron anyway**, while DeepSeek was still serving. Two
RAM-heavy models resident simultaneously.

The code already *detects* this state. `models.py:109` reads:

```python
if _get_process(other_id) is not None or is_script_model_loaded(other_id):
```

The `or` branch exists specifically to catch "running but untracked." But the
remediation it invokes (`unload_script_model`) can only kill tracked handles.
Detection without enforcement — Operating Rule 6, in the code.

## 3. Defect 2 — a locked thread pinned to an unloaded model is a dead end

`restoreThreadModelState` (`src/static/threads.js:42`) writes the saved model
into the selector and disables it when the thread is locked. A programmatic
`.value` assignment fires no `change` event, and the load-confirm modal opens
from exactly one place — `src/static/app.js:810`, inside that `change`
listener. There is no load control anywhere else; the eject button unloads only.

**Reproduced live** (real browser, real `data/threads.json`, DeepSeek genuinely
unloaded):

```
activeThreadId: 1 | selectValue: "deepseek-v4-flash"
selectedOption.dataset.loaded: "false"
selectDisabled: TRUE | loadModalHidden: true | ejectHidden: true
POST /api/v1/chat with that model → HTTP 422 "Model deepseek-v4-flash is not loaded"
```

Thread 1 (31 messages) is `locked: true`. **26 of 47 threads** are locked *and*
pinned to a script model. On a locked thread the report's stated workaround
("switch to another option and back") is unavailable — the selector is disabled.
Recovery requires leaving the thread entirely.

## 4. Defect 3 — documented run command collides with DeepSeek (FIXED HERE)

`README.md` and `CLAUDE.md:45` both instructed `uvicorn src.main:app --reload`,
which binds `127.0.0.1:8000` (uvicorn `Config` default host and port). That is
DeepSeek's port: `DS4_URL` defaults to `http://127.0.0.1:8000`, `.env` sets no
override, and `run-server.sh` hardcodes `--host 127.0.0.1 --port 8000`.
`.claude/launch.json` — what the CEO actually uses — has always said 8080.

Both files corrected in this commit.

**Two corrections to the original report:**

- **Timing.** It fails in **8.0 s** (measured), not after the 180 s timeout.
  `load_script_model` breaks its wait loop at `models.py:128` as soon as
  `process.poll()` is not None, and a bind-failing child exits immediately.
  The *message* still reads `timeout waiting for...`, which is misleading, but
  no one waits three minutes.
- **The "silent hijack" row is unreachable** from the documented command. It
  requires the app to bind `0.0.0.0`; uvicorn defaults to `127.0.0.1` and no
  doc in this repo instructs otherwise. The underlying OS behavior is real but
  conditional — wildcard-then-specific succeeds only when the second socket
  sets `SO_REUSEADDR`. Also verified: the app returns 404 on `/v1/models`, so
  it never falsely advertises itself as a loaded DeepSeek.

---

## 5. Root cause — the spec specifies mechanisms, not outcomes

The tests did not miss these. They faithfully encode acceptance criteria that
describe *what the code should do* instead of *what should then be true*.

The unload test asserts `send_signal` was called on a `MagicMock`. A mock always
accepts a signal; there is no process that can fail to die. It is a correct
implementation of AC-95:

> **AC-95:** WHEN the user clicks Unload DeepSeek THEN the backend SHALL SIGINT
> the process (5 s grace, SIGKILL after) and return `{"status":"unloaded"}`.
> Unload while the model was not loaded is a 200 no-op.

Mechanism (send a signal) and response string. Never *"the model is no longer
running."* The final clause specifies the defect into existence: the spec
assumes one meaning of "not loaded," while the code has two — no tracked handle,
and not answering on 8000. A restart makes them disagree, and the code follows
the spec.

### 5.1 Spec lint across the whole frozen spec

77 AC statements were reconstructed from 33 PRD versions in git history (the
PRD is replaced at each refreeze). For every AC governing an operation that
changes resource state: does the SHALL clause state an observable
post-condition, or only an action?

**The failure is not spread out — it is confined entirely to process lifecycle.**

**Data/file lifecycle — 9 of 9 pass.** AC-35 ("persist *such that a subsequent
GET returns the updated thread*"), AC-37 ("*so that a following GET returns an
equal payload*" / "*leave the stored snapshot unchanged*"), AC-77 ("*persist
nothing*"), AC-78 ("*bytes preserved*"), AC-82 ("*.bak always holds exactly the
previous snapshot*"), plus AC-38/41/79/91. Written impeccably.

**Process lifecycle — 5 of 8 fail.**

| AC | Verdict | Why |
|----|---------|-----|
| AC-4 (load) | pass | "respond 'loaded' **once the HTTP readiness probe succeeds**" |
| AC-5 (load, already up) | pass | "**without spawning a second instance**" |
| AC-6 (timeout cleanup) | **fail** | "SHALL terminate the spawned process (SIGINT → SIGKILL)" — mechanism only |
| AC-7 (unload) | **fail** | "SHALL send SIGINT and respond 'unloaded'" |
| AC-94 (DeepSeek load) | half | load half polls readiness; failure half is "SIGINT, clear the handle" |
| AC-95 (DeepSeek unload) | **fail** | mechanism + response string |
| AC-96 (mutual exclusion) | **fail** | "SHALL **unload the first**" — names the call, not the outcome |

The comparison that contains the entire root cause, from one document:

> AC-35: persist **such that a subsequent GET returns the updated thread**
> AC-95: SIGINT the process and **return `{"status":"unloaded"}`**

Nobody wrote the process equivalent of *"such that a subsequent GET returns…"* —
which is *"such that a subsequent readiness probe fails."* Note also AC-4 vs
AC-95: **load is outcome-specified, unload is mechanism-specified, in adjacent
criteria.** That asymmetry is exactly why loading works reliably and unloading
does not.

### 5.2 AC-7 × AC-8 leave a quadrant undefined — and it is Defect 1

|  | tracked handle | no tracked handle |
|--|----------------|-------------------|
| **reachable** | AC-7 → SIGINT | **no AC exists** |
| **not reachable** | AC-8 → 200 no-op | AC-8 → 200 no-op |

AC-7 is the only place in all 77 ACs where "tracked handle" appears. The empty
cell is precisely the post-restart state. AC-95 later collapsed the 2×2 into
"unload while the model was not loaded is a 200 no-op," resolving the undefined
cell in the wrong direction.

### 5.3 AC-15 was orphaned by M8, then inverted by a frozen test

> **AC-15:** WHEN the page is refreshed, THE SYSTEM SHALL **unlock the model
> selector** and refresh its contents.

AC-15 and AC-25 both defined refresh semantics. M8 added persistence and
explicitly retired AC-25 (`tests/test_ui.py:136` — *"AC-34 [M8 — replaces
AC-25: refresh now RESTORES]"*). **AC-15 was never retired.** That same M8
replacement test ends:

```python
expect(page.get_by_test_id("model-select")).to_be_disabled()
```

The frozen suite asserts the exact opposite of a live acceptance criterion. No
test pins AC-15 (zero references in `tests/`). **AC-15 was Defect 2's escape
hatch** — refresh unlocks, the user re-picks, the load modal fires. It was
specified, silently contradicted, and never reconciled.

The pipeline has a retrofit mechanism for exactly this (AC-27..AC-33 are all
labeled *"retrofits AC-N, broke in M6"*), but it is reactive: someone has to
notice. Nothing detects that a new AC or test contradicts a live one. Refreeze
only hashes files.

**Audit coverage caveat:** 23 ACs have no recoverable statement text. All are
UI/theme/markdown/rename — none are process lifecycle. AC-48 (Stop mid-stream)
is a cancellation operation in the same class and is unaudited.

---

## 6. Proposed spec delta (TPM input — not yet frozen)

These are drafted for the TPM web chat. They are **not** authoritative until
they land via `scripts/refreeze.sh`.

**AC-95′ (replaces AC-95).** WHEN the user requests unload of a script model,
THE SYSTEM SHALL terminate that model's server **such that, after the call
returns, the model's readiness probe fails and its port is no longer bound** —
regardless of whether a subprocess handle is tracked, and regardless of whether
the process was spawned by the current app process. WHEN no server is running
for that model, the call SHALL be a 200 no-op. WHEN a server is running but
cannot be terminated, THE SYSTEM SHALL respond `{"status":"error"}` and SHALL
NOT report `"unloaded"`.

**AC-96′ (replaces AC-96).** WHEN a script model is requested AND any other
script model is running, THE SYSTEM SHALL, before spawning the requested model,
bring the other model to a state where **its readiness probe fails**. IF that
cannot be achieved, THE SYSTEM SHALL NOT spawn the requested model and SHALL
respond `{"status":"error"}`.

**AC-7′ / AC-6′.** Restate in outcome form; AC-7′ subsumes the undefined
quadrant by dropping "tracked subprocess handle" from the precondition
entirely — reachability is the only state that matters.

**AC-15 disposition.** Either formally retire it (superseded by M8 persistence),
or — preferred — replace it with an outcome that closes Defect 2:

**AC-101 (new).** WHERE a thread's pinned model exists in the catalog but is not
loaded, THE SYSTEM SHALL provide a path to load it from that thread **in no more
than two interactions**, including when the thread's selector is locked.

**Also needed:** the `_terminate_process` implementation must reach servers it
did not spawn (PID discovery by port or by launch command — `src/api/status.py`
already does the latter for RSS reporting via `_script_model_rss_gb`), and the
`load_script_model` failure message should stop saying "timeout" for a fast
child-exit.

---

## 7. Proposed permanent gate

At refreeze, for any AC whose verb changes resource state (spawn / terminate /
kill / unload / evict / delete / release / clear / cancel), require a
post-condition clause naming an observable check. Mechanically greppable, in
the spirit of BLUEPRINT Rule "a rule that cannot be enforced mechanically is a
suggestion." It would have caught AC-6, AC-7, AC-94, AC-95, and AC-96 **before
they were frozen**.

A second, cheaper gate: fail refreeze when a staged test's assertions contradict
a live AC that no delta retires (the AC-15 case). Weaker to automate; at minimum,
require every delta to list the ACs it supersedes, and diff that against ACs
whose behavior the staged tests touch.

---

## 8. Verification log (2026-07-25)

All performed against `c4710cc` with the app otherwise stopped. No production
state was mutated: `data/threads.json` verified byte-identical
(`bcab36da...`) before and after; `git status` clean throughout the
investigation; every spawned test process cleaned up.

| Check | Result |
|-------|--------|
| `git diff 1204546 c4710cc` | empty — byte-identical premise holds |
| unload with empty handle dict + live server | `{"status":"unloaded"}`, process alive, port held |
| `uvicorn --reload` file-save orphaning | worker killed, child survived `PPID=1` |
| mutual exclusion with untracked orphan | second model spawned anyway |
| locked thread, unloaded pinned model | selector disabled, no modal, chat 422 |
| unlocked thread, unloaded pinned model | two-step reselect does open the modal |
| port-8000 collision failure time | 8.0 s (not 180 s) |
| app response on `/v1/models` | 404 — no false "loaded" reading |
| wildcard vs specific bind | succeeds only with `SO_REUSEADDR` on the second socket |
