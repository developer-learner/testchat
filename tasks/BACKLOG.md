# BACKLOG.md — Task Queue

> Ordered by priority. Top = next up.
> When starting a task, move it to CURRENT.md and expand it into a full spec.

---

## Up Next

### User-understandable chat error copy (distinct plain cause + retry)
**Priority:** P2 — CEO-decided 2026-09-03; slotted, not started. When a chat
fails the user should see the actual cause in plain language (e.g. "The model
failed to load."), with NO suggestions and retry as the only action. It's a
freeze (the current spec pins the generic line + a "pick a local model"
suggestion in `test_chat_api.py` and `test_router_route.py`), ~1 hour. Full
design + ready code: [`tasks/llm-error-copy-design.md`](llm-error-copy-design.md).


### ~~Discover models from generic OpenAI-compatible endpoints~~ — REMOVED 2026-08-08
**Priority:** ~~P1~~ — struck by CEO decision: not needed. Contrary evidence
noted (MTPLX chat works but the model is unselectable), but generic
`/v1/models` discovery is out of scope by direction. **Original entry
retained below for provenance:**

**Why:** Live deployment against MTPLX on 2026-07-30 proved that chat
completions work end to end (`APP_OK` through `/api/v1/chat`), but the browser
cannot select the model. `list_models()` probes only LM Studio's non-standard
`/api/v1/models` catalog; MTPLX correctly exposes the standard `/v1/models`
shape. With both script-run models unloaded, the selector therefore shows no
loaded model and Send remains disabled. This contradicts the product promise
that testchat works with any OpenAI-compatible local endpoint.
**What:** New frozen-spec milestone: the configured endpoint must expose an
LM Studio catalog, discover served model IDs from the standard OpenAI `GET
/v1/models` response, expose them as loaded remote models, and allow the UI to
select and route to them. Preserve LM Studio behavior and script-model
load/unload semantics. Tests must be TPM-authored and installed through
`refreeze.sh`; EM/coder work must run through `orchestrate.sh`.
**Rough size:** Spec + API/service tests + `services/models.py` + model source
schema (and UI test only if existing generic-model behavior is insufficient)

### ~~Guard against control-plane manifest drift on doc edits~~ — DONE 2026-08-08
**Priority:** ~~P2~~ — shipped as the warning-only
`scripts/manifest-drift-guard.sh`, wired into `.githooks/pre-commit`. When a
staged control-plane file changes without its matching manifest update, the
guard names the file and prints the exact `scripts/regen-manifest.sh` command.
It never regenerates or blesses the manifest itself; the existing manifest
gate remains the fail-closed enforcement point. Selftests cover project- and
template-manifest drift plus the clean path. The original recurrence was
`7537d83` (gate red) → `68b2b2a` (hand re-pin).

### ~~AC-95′/AC-96′ recut — "unloaded" must mean the process is gone~~ — SHIPPED
**Priority:** ~~P0~~ — **DONE 2026-07-26, M29 (spec v58 → v59).** Recut as
AC-102..AC-106 in outcome form; `unload_script_model` now discovers the server
by the **listening port** parsed from its `ready_url` (`_find_listening_pid`,
per-process `psutil.process_iter()`), terminates that one PID, re-probes, and
returns `{'status':'error'}` when the model is still reachable. Load aborts
rather than spawning when the other model cannot be evicted. 153/153 on the
macOS host, in the sandbox container, and in CI. Discovery by process *name*
was rejected by CEO directive: `pgrep -f <basename>` also matches unrelated
processes that merely mention the script path, then SIGKILLs them. Original
entry retained below for provenance.
**Why:** Confirmed live 2026-07-25. `unload_script_model` returns
`{"status":"unloaded"}` whether or not it had a handle to kill. Process handles
live in a module-level dict (`src/services/models.py:50`) that any uvicorn
worker restart empties — verified: a file save under `--reload` kills the
worker and orphans its `Popen` child to `PPID=1` (uvicorn
`basereload.py:96` signals the worker PID only). After that, unload reports
success, the server keeps running, keeps the port, and the catalog still says
`loaded: true`. Worse: the RAM mutual-exclusion guarantee silently fails —
with a live-but-untracked model, `load_script_model` calls unload (no-op) and
**spawns the second model anyway**. Two RAM-heavy models resident.
**Root cause is the AC, not the test.** AC-95 specifies a mechanism ("SHALL
SIGINT the process ... and return `{"status":"unloaded"}`") and never an
outcome. The frozen test correspondingly asserts `send_signal` on a
`MagicMock`, which cannot fail. AC-7×AC-8 also leave "reachable but untracked"
— exactly the post-restart state — undefined.
**What:** TPM re-cut of AC-95/AC-96 (and AC-6/AC-7/AC-94's cleanup halves) in
outcome form: terminate *such that the readiness probe fails and the port is
unbound*, regardless of whether a handle is tracked or who spawned the process.
Implementation must reach servers it did not spawn — `src/api/status.py`
`_script_model_rss_gb` already does PID discovery by launch command and is the
obvious model. Draft ACs in
`project-trail/2026-07-25-unload-spec-lint.md` §6.
**Rough size:** Spec + test + `services/models.py`

### ~~Invert the `no_edit_files` default~~ — DONE 2026-07-26 (`2144d12`)
**Priority:** ~~P0~~ — shipped. Permitted set is now derived from the frozen
delta via `--affected` instead of hand-listed; an existing file the delta does
not touch never reaches the coder, while a not-yet-existing file stays editable
so greenfield builds still work. Verified on the M29 plan: 8 of 12 files
blocked, up from 3. **Residual:** `--affected` includes transitive dependents,
so `app.js` and `chat.py` remain editable for a models-only delta, and `app.js`
maps 0 tests (smoke_check only). Tightening to direct hits is a separate call.
**Original entry:**
**Why:** Near-miss 2026-07-26 during M29. `.pipeline-state/tasks/` had lost its
per-task `done` markers, so the EM planned all 12 files with every task
`pending`. `contracts.no_edit_files` protects only 3 (`markdown.js`, `rain.js`,
`style.css`), so the coder was about to be handed the other 9 — `app.js`,
`chat.py`, `threads.py`, `index.html`, `websearch.py` — none of which the M29
delta touches. Caught by inspection before the first coder call, not by any
gate. D-65 exists precisely to keep declared-unchanged files away from the
coder; it is scoped too narrowly to do that job.
**What:** Invert the default. A file NOT named in the delta's
`changed_contract_ids`/`changed_files` should be no-edit for that milestone,
rather than fair game. Derive the no-edit set at refreeze instead of hand-listing
it, so it cannot drift.
**Rough size:** `refreeze.sh` + `orchestrate.sh` no-edit lookup + a DECISIONS entry

### ~~Fail closed when pipeline task-state is missing~~ — DONE 2026-07-26 (`6557283`)
**Priority:** ~~P0~~ — shipped. Pre-flight halts when `.pipeline-state/tasks/`
is empty while the repo has prior `[task ` commits: that combination is lost
state, never a greenfield start. Verified by simulation — orchestrate halted at
pre-flight with recovery guidance before touching anything. An intended rebuild
stays one explicit `rm -rf .pipeline-state` away.
**Original entry:**
**Why:** Same 2026-07-26 near-miss, other half. An empty
`.pipeline-state/tasks/` is indistinguishable from a greenfield repo, so
orchestrate treats "state lost" as "nothing built yet" and rebuilds everything.
The directory is gitignored and unversioned, and has now gone missing twice
under this tree (the `.tpm/outbox/` disappearance, then a *partial* delete that
emptied `tasks/` while `refreeze-pending.diff` survived beside it).
**What:** Halt with a clear message when `.pipeline-state/tasks/` is empty AND
`src/` is populated AND the frozen suite is mostly green — that combination is
lost state, never a fresh project. Offer the reconstruct path rather than
silently planning a full rebuild.
**Rough size:** `orchestrate.sh` pre-flight

### ~~Run the frozen suite unprivileged in the sandbox~~ — DONE 2026-08-08 (D-127)
**Priority:** ~~P1~~ — closed after truthful premise correction. The sandbox
has run as non-root `agent` (UID 1000, `USER agent` in the Containerfile)
since the template bootstrap — verified inside the dev-vm: sandbox `id -u`
returns 1000, `Uid:`/`Gid:` all 1000, under `--userns=keep-id
--cap-drop=ALL --security-opt no-new-privileges`. M29's incident was a
macOS-vs-Linux psutil semantics gap (module-level `net_connections()`), not
a container privilege gap; the per-process form already landed. The real
gap: nothing PROVED the property — the constraint-2 verifier never checked
the process user. Closed with `verify along in D-127`: the verifier now
asserts non-root (check 6), so a regression to `USER root` in the image
fails selftests outright. The "never declare green without a host run"
interim rule is superseded for the user-privilege axis (still standing for
platform-specific code like macOS root calls, per M29).

### Spec lint, reverse direction — live tests vs NEW ACs
**Priority:** ~~P1~~ — closed 2026-08-08 with S6 (D-128): `scripts/check-test-direction.py`
preflight, wired into `refreeze.sh` after INV-4. It rejects (1) a suite mock —
carried or staged — that answers every URL (a URL-verb fake whose callable
never reads its URL parameter, or a bare `Mock()`), and (2) a carried-forward
test that cites an AC id this delta adds. Runs on the merged preview suite, so
neither side of the delta escapes. 303 selftests pin it in both repos
(whole-world mock rejected, carry-citation rejected, URL-scoped fake accepted).
**Why:** The existing lint checks staged tests against live ACs. v58 passed it
and still shipped a contradiction in the other direction: the carried-forward
`test_load_nemotron_expands_script_path` monkeypatches `httpx.get` to return
200 for **every** URL, which makes the *other* script model read as loaded, so
new AC-104 correctly refuses to spawn and `Popen` is never called — while the
test asserts it was. Unsatisfiable alongside AC-104; cost a full escalation
cycle and the v59 refreeze to fix.
**What:** (a) diff live carried-forward tests against the ACs a delta ADDS, not
only staged tests against live ACs; (b) treat a mock that answers every URL as
a lint failure — it encodes "the whole world is ready" and silently couples
unrelated subsystems.
**Rough size:** `check-test-surface.py` or a new refreeze lint — shipped as the
latter.

### S6 residual — 9 sandbox-frozen whole-world mocks still held in the suite
**Priority:** P3
**Why:** D-128 scopes S6's whole-world-mock check to delta-touched tests;
test_models_api.py:140,166,319 and test_models_service.py:159,181,190,202,214,357
carry 9 legacy bare-Mock patterns, grandfathered by design (re-cutting old
content must not gate every future refreeze). The class is still live in the
suite; a future test that interacts with one of those subsystems must mock the
real seam, and S6's check 2 (carried test citing a NEW AC) is the net if it
doesn't.
**What:** Re-cut those 7 sites via the TPM bundle only when a refreeze is
already scheduled for other reasons — no standalone freeze just for this.
**Rough size:** Spec/test-only

### ~~Halve the full-suite wall clock (freeze-time floor)~~ — RETIRED 2026-08-14
**Priority:** ~~P2~~ — superseded by the current scoped test paths. D-112
removed the full suite from ordinary milestone completion: the verdict runs
only the delta-mapped node-ids. `refreeze.sh` likewise does not execute the
full suite; it performs sandbox collection plus the D-75 delta-only
red-before-green check. The full suite now runs only when explicitly requested
through `orchestrate.sh --full-suite`, so it is neither a freeze-time floor nor
a recurring milestone cost. Changed-tests-first ordering therefore has no
remaining recurring run to optimize. `pytest-xdist`/parallel report-merging is
also retired: it would add shared-server, fixed-port, and shared-storage risk
for an on-demand check, not shorten the normal milestone path. Revisit only if
measured evidence shows on-demand regression checks have become an operational
bottleneck.

### ~~Fold `mypy` into the sandbox run~~ — DONE 2026-08-08 (D-129)
**Priority:** ~~P2~~ — shipped. `run_tests()` now type-checks `src/` in the
sandbox before pytest; a type error fails acceptance rc=1 (`FAILING=mypy:src`)
without launching pytest. Wired blueprint-first (template-owned files), synced
via template-update; 306 selftests green both repos. Also resolved this
session: the wall-clock (c) concurrent backend lane is DROPPED — measured
~40s ceiling that mostly no longer applies post-D-112 (full suite off the
per-milestone verdict path), and it touches the verdict-computation path for
net-negative risk. Mypy **Alternative considered — wall-clock (c)**: rejected
at scoping (see above). **Original entry:**
**Why:** CI's type-check is a gate nothing local exercises — the sandbox runs
pytest and ruff only. M29's `psutil` addition passed two full platform runs at
153/153 and still broke CI on `Library stubs not installed for "psutil"`,
costing a red build and a follow-up commit (`types-psutil`, `0eb1d38`).
**What:** Add `mypy --explicit-package-bases src/` to the sandbox acceptance so
CI-only gates stop existing.
**Rough size:** `sandbox-run.sh` + `orchestrate.sh` acceptance

### ~~`em.md` — test node-ids must be copied verbatim~~ — DONE 2026-08-08
**Priority:** ~~P2~~ — shipped. One line added to `em.md`'s plan requirements:
"copy each node-id EXACTLY as it appears in `test-nodeids`, including any
parametrization suffix such as `[chromium]` — the plan gate rejects an id that
does not match the frozen suite byte-for-byte." Landed template-first (blueprint
`9a623c6`, `.manifest-template` regenerated in the same isolated commit per
Rule 2) then synced to testchat (`05418dc`); 300 selftests green in both repos.
**Original entry:**
**Why:** The EM emitted all 32 `test_ui.py` / `test_ui_websearch.py` node-ids
without Playwright's `[chromium]` parametrization suffix, so the plan gate
rejected every one as "not in the frozen suite" and burned a plan revision.
`scripts/.approved/test-nodeids` carries the suffix; `.opencode/prompts/em.md`
never says to copy ids verbatim. It self-corrected on the retry, but will
recur on any delta touching parametrized tests.
**What:** One line in `em.md`: copy node-ids exactly as they appear in
test-nodeids, including parametrization suffixes. Note `em.md` is control-plane
and hash-pinned — regenerate `scripts/.control-plane-manifest` in the same
isolated commit (Rule 2).
**Rough size:** prompt line + manifest regen

### ~~AC-15 disposition + AC-101 — a pinned unloaded model must be loadable~~ — SHIPPED
**Priority:** ~~P1~~ — **DONE 2026-07-28, M32 (spec v71).** AC-28 was
retired and AC-133..AC-135 replaced the dead-end lock with free model
selection: the selector stays enabled across thread states, model choice is
sticky per thread, and a mid-chat change updates the stored model and routes
the next send accordingly. The legacy `locked` field remains persisted only
for backward compatibility and is no longer read by the UI.

**Original entry:**
**Why:** Confirmed live 2026-07-25. Thread 1 (31 messages) pins
`deepseek-v4-flash`; the model is unloaded; the selector shows it and is
**disabled** because the thread is `locked`. The load-confirm modal opens from
exactly one place (`src/static/app.js:810`, a `change` listener), and a
programmatic `.value` set fires no `change`. Sending returns HTTP 422. **26 of
47 threads** are locked and pinned to a script model. On a locked thread there
is no workaround at all — recovery requires abandoning the thread.
**Spec-integrity defect behind it:** AC-15 ("WHEN the page is refreshed, THE
SYSTEM SHALL unlock the model selector") was the escape hatch. M8 added
persistence, explicitly retired AC-25, and left AC-15 orphaned — and the M8
replacement test now ends `expect(model-select).to_be_disabled()`, asserting
the opposite of a live AC. No test pins AC-15.
**What:** Formally retire AC-15, and add AC-101: WHERE a thread's pinned model
exists in the catalog but is not loaded, the system SHALL provide a path to
load it from that thread in ≤2 interactions, including when the selector is
locked.
**Rough size:** Spec + test + `static/app.js` (likely a load affordance beside
the eject button)

### ~~Spec lint at refreeze — post-conditions for state-changing ACs~~ — SHIPPED (S5)
**Priority:** ~~P1~~ — closed 2026-08-08: `scripts/check-ac-postconditions.py`
is wired as the S5 pre-check in `refreeze.sh:235`. Original entry retained
below for provenance:
**Why:** The two defects above share one cause. A lint over 77 ACs
reconstructed from 33 PRD versions found it confined entirely to process
lifecycle: **5 of 8 process ACs fail**, while **9 of 9 file-lifecycle ACs
pass**. AC-35 says "persist *such that a subsequent GET returns the updated
thread*"; AC-95 says "SIGINT the process and return `{status:unloaded}`". Same
document, opposite discipline. Load is outcome-specified (AC-4, "once the HTTP
readiness probe succeeds"), unload is mechanism-specified — which is why
loading is reliable and unloading is not.
**What:** Gate at refreeze — any AC whose verb changes resource state
(spawn/terminate/kill/unload/evict/delete/release/clear/cancel) must carry a
post-condition clause naming an observable check. Greppable. Second, weaker
gate: every delta lists the ACs it supersedes, diffed against ACs whose
behavior the staged tests touch, so a staged test cannot contradict a live
un-retired AC (the AC-15 case). Likely blueprint-side — see
`tasks/HANDOFF-blueprint-items.md`.
**Rough size:** `scripts/` + BLUEPRINT

### ~~AC-48 audit — Stop-mid-stream is an unaudited cancellation AC~~ — DONE (v87, 2026-08-08)
**Priority:** ~~P3~~ — all text re-applied at `refreeze v87` (`a520c46`): re-cut
AC-48 criterion + "such that the stream ends and no further tokens arrive"
post-condition clause placed in the PRD; citing tests restaged with the delta
to retire the S6 carried-claim; preflights green and the frozen tests verified
in the sandbox. Entry retained below for provenance of the audit:
**Why:** The 2026-07-25 lint recovered 77 of ~100 AC statements; 23 have no
surviving PRD text. All 23 are UI/theme/markdown/rename **except AC-48**
(deliberately slow stream so a test can click Stop mid-reply), which is a
cancellation operation — the same class as the failing process-lifecycle ACs
and never checked for a post-condition.
**What:** Recover AC-48's text and apply the §5.1 lint.
**Rough size:** Spec review only
**Verdict (2026-08-08):** Text recovered verbatim from freeze v20 (`51149c1`):
"AC-48 (stop): WHILE a reply is streaming, THE SYSTEM SHALL present the send
control as 'Stop'; WHEN the user clicks it after visible text has arrived, THE
SYSTEM SHALL end the stream, keep the partial reply in the thread, and restore
the 'Send' control." Applied the §5.1 lint: **FAILS** — "end the stream" is
mechanism, not outcome; no `such that` post-condition clause naming an
observable check. The frozen test (tests/test_ui.py:229, M10 ratify) does pin
the observable pair the lint wants ("Send" restored, partial reply retained,
control re-enabled), so the coverage exists in test form — but the PRD text
never carried the post-condition, and per D-31 the PRD only changes via
refreeze. Re-cut text drafted into the PRD: add "such that the
stream ends and no further tokens arrive" as the post-condition clause.

### ~~AC-42 flake hardening — test_thinking_placeholder_shows_then_clears~~ — DONE (v55 recut)
**Priority:** ~~P1~~ — closed 2026-08-08: the recut **already shipped at
`51cb22e` [refreeze v55]** (2026-07-19, M23d). `tests/conftest.py` gates
the answer tokens behind `_slowping_gate` and the test releases via
`/release-slowping` — no wall-clock hold remains (the "~1.2s hold window
was missed" failure is the pre-v55 stub). v58-era amendments retained the
gate (frozen-manifest conftest hash `99bdc97b`). Verified today: 7/7 green
in the sandbox with the pipeline invocation, including a 700MB in-container
memory-stress run. Original entry retained below for provenance:
**Why:** M9-era timing-sensitive SLOWPING placeholder test; intermittent
in full-suite runs. Flagged for hardening 2026-07-15 ("harden both at the
M23 refreeze") but never done; on 2026-07-19 it failed three M28 close-out
runs and forced a CEO-authorized manual `[success]` bypass (`69708e4`).
Stability defect against M9, not any current milestone.
**Update (2026-07-19 later session):** now reproduces IN ISOLATION under
memory load (nemotron + LM Studio model both resident): 4/4 consecutive
failures, including at a clean commit (A/B-exonerated an unrelated
markdown live-fix). Failure detail confirms the race — by first expect()
attach the full reply had streamed; the ~1.2s hold window was missed.
"Passes in isolation" only holds on an unloaded machine.
**What:** TPM re-cut of the AC-42 test at the next refreeze (test is
INV-1-frozen; only path is `scripts/refreeze.sh`). The complementary
pipeline fix (D-77, retry-in-isolation before DRIFT) is blueprint-side,
parked in `tasks/HANDOFF-blueprint-items.md`.
**Rough size:** Spec/test-only

### ~~AC-47 recut — thread-delete confirm off native window.confirm~~ — DONE (v55 + live-fix)
**Priority:** ~~P2~~ — closed 2026-08-08: the recut **already shipped**.
Test re-cut at `51cb22e` [refreeze v55] (M28d: `test_thread_delete_removes_thread`
clicks `delete-confirm`, no `page.once("dialog")`); the `deleteThread` →
`confirmDelete()` swap landed as live-fixes `2f25d4e` + `1fa18ed`.
Verified today: `test_thread_delete_removes_thread` green in the sandbox
(3/3 in the same run as the AC-42/AC-48 tests).
**Why:** CEO wants all confirms themed (2026-07-19). Message-pair delete
now uses the themed delete-confirm-modal (live-fix), but thread delete
must stay `window.confirm` because frozen AC-47
(`test_thread_delete_removes_thread`) drives it via `page.once("dialog")`
— a custom modal leaves the thread undeleted and fails the suite.
**What:** TPM recuts AC-47 to click the modal's confirm button; then
`deleteThread` switches to the same `confirmDelete()` helper in
threads.js (one-line swap, code path already exists).
**Rough size:** Spec/test + one-line code change

### ~~M13 — app.js module split (spec backfill)~~ — DONE 2026-07-27 (v66, `361fbe4`)
**Priority:** ~~P2~~ — shipped. The 2026-07-27 second split (chrome.js +
catalog.js, commit `2579f07`) plus the v66 ratify freeze cover the full
current module layout: `app.js` (chat surface), `chrome.js` (themes /
focus / settings / modal chrome), `catalog.js` (model dropdown lifecycle),
`threads.js`, `markdown.js`, `rain.js`, `current-chat.js`,
`sidebar-resize.js`. ERD `As-built architecture` names each; smoke_checks
present for all. The first split's files (markdown.js, threads.js) were
already in the inventory pre-v66. See
`project-trail/2026-07-27-appjs-split-handoff.md`.
**Original entry:**
**Why:** Split already landed as live-fix (markdown.js, threads.js, app.js);
needs TPM spec coverage if pipeline work resumes
**Rough size:** Spec-only (code done)

### status.py RAM-helper coverage — the standing gap behind the coverage floor
**Priority:** P2
**Why:** `src/api/status.py` sits at **38% (61 of 99 statements never executed
by any test)** — far the worst file in the tree; next worst is storage.py at
70%, everything else is 77-100%. It is also what caps the CI coverage floor:
raised 75 → 79 on 2026-07-24 (`9469c7b`), and total coverage is 79.8-80.2%
depending on platform. Closing most of this gap is what makes an 85 floor
reachable. Nothing here is a known bug — it is unverified code, which is a
different and quieter risk.
**What is uncovered** (`--cov-report=term-missing`, spec v57):
lines `27, 32-41, 49-80, 85, 94-128` — i.e. essentially the whole of
`_ram_totals()`, `_script_model_rss_gb()`, `_nemotron_rss_gb()` and
`_loadable_gb()`. `get_status()` itself IS covered by `test_status_api.py`.
**The catch — read before scoping:** these helpers shell out to `sysctl -n
hw.memsize` and `vm_stat`, which are **macOS-only**. On the Linux CI runner
the subprocess call raises, the `except Exception` branch swallows it, and the
happy paths are structurally unreachable — this is the documented mac/Linux
delta in `ci.yml` (measured 83% on macOS vs 78% on Linux back on 2026-07-14).
So this is NOT "write the obvious tests"; it needs a deliberate choice:
  (a) test the PARSING against captured fixture output with `subprocess.run`
      monkeypatched — highest value, since the `vm_stat` page-accounting parse
      (lines 32-41) is exactly the kind of string handling that breaks
      silently on an OS update and would never be noticed; the suite already
      monkeypatches in `conftest.py`, `test_websearch_service.py` and
      `test_nemotron_config.py`, so the pattern exists; or
  (b) accept the gap as platform-inherent and record that decision so the
      number stops looking like neglect.
Option (a) is the recommendation; (b) is a legitimate CEO call.
**Constraint:** tests are INV-1-frozen — no agent may author them. This needs
a TPM spec + `scripts/refreeze.sh`, not a patch. That is also why it never got
done incidentally.
**Rough size:** Spec/test-only (no `src/` change expected)
**Source:** 2026-07-24 coverage-ratchet session.
**DECIDED 2026-08-08 (b — accept and record):** doesn't ship the CEO-judged
platform-specific helpers; status.py stops reading as neglect — a documented
decision, not an oversight. The fixture tests (monkeypatched `subprocess.run`
over captured `sysctl`/`vm_stat` output) are not lost: they fold into a later
TPM refreeze that already touches this file for another reason — no standalone
freeze for coverage alone (the refreeze floor costs more than the coverage
earns; 38%→~85% on the CI floor is still gated on the mac/Linux delta).

---

## Later

### ~~Model add/unload has issues — run a small test LLM through user use cases, note and fix~~ — SUPERSEDED 2026-09-03
**Priority:** ~~P2~~ — parked by CEO direction (2026-09-03): testchat relies on
Vortex for model load/unload; the in-house loader (`src/services/models.py`
lifecycle) is frozen as-is and gets no further work. The rough edges below are
Vortex's concern now, not testchat's. Original entry retained for provenance:

**Why:** Model add/load/unload has known rough edges discovered in 2026-08-15
session work, but no focused pass has classified them. Known so far:
- Terminating testchat (SIGINT/SIGTERM, Ctrl+C on `uvicorn`) does NOT unload
  spawned script models — models.py has no shutdown/lifespan handler, so child
  engine processes are orphaned (still running, RAM held) after the app dies.
  Sidecars (`data/model-sidecars/`) survive by design so a restarted app can
  take ownership and Eject them, but a dedicated unload-all-on-exit hook is
  absent.
- To be surfaced by the use-case pass: load-confirm flow, eviction/mutual
  exclusion, cancel-mid-load, port collisions, engine crash, double-Eject.
**What:** Use a small fast test LLM (e.g. a tiny GGUF reached at ~high tok/s)
and walk the real user flows — load from the dropdown, send while
thinking/streaming, Eject, load another model (eviction), kill the engine
process externally, restart testchat mid-load — and catalog every defect with
a repro + expected behavior, then fix. This is deliberately "for later":
session value is higher in the router extraction (below) first.
**Rough size:** investigation pass + a handful of small direct fixes.

### ~~Model router app — unified engine manager testchat (and other apps) refer to~~ — SUPERSEDED 2026-09-03 (Vortex is this router)
**Priority:** ~~P1~~ — closed by CEO direction (2026-09-03): **Vortex** is the
standalone engine-manager/router this item proposed building. testchat delegates
model load/unload to Vortex rather than extracting its own router, and the
in-house loader (`src/services/models.py`) is frozen as-is — no further work.
Original entry retained for provenance:

**Why:** testchat currently owns engine lifecycle inline in
`src/services/models.py` (SCRIPT_MODELS registry + spawn/ready-probe/terminate
+ sidecars) and hard-codes the per-engine launcher scripts
(`scripts/run-server-0731-*.sh`, ds4 `run-server-0731.sh`) and their ports.
That couples every consumer of these engines to a testchat-specific process
manager. Extract it into a standalone **router app** that:
- Owns the full engine inventory: `omlx`/`antirez` (ds4 0731), `llama.cpp`
  (`llama-server` unsloth GGUFs), LM Studio, mtplx — spawn, ready-probe,
  terminate, evict-on-load, mutual exclusion, sidecar identity.
- Exposes a management surface (catalog, loaded-state, load/unload) so testchat
  delegates model handling to it instead of embedding it.
- Exposes a **universal OpenAI-compatible service** (`GET /v1/models`,
  `POST /v1/chat/completions`, SSE) so ANY app — testchat, OpenCode, the pi
  agent — can consume the loaded models through the router without
  understanding engines at all.
**Check asked:** confirm the router can present a generic `/v1/*` surface that
other OpenAI-compatible clients (opencode, pi agent) can target unchanged, and
that LM Studio models still route through it alongside script engines.
**Rough size:** new standalone service repo + thin testchat integration
(drop-in for `services/models.py`); likely its own freeze/milestone trajectory
per the repo rules.

## Later (existing)

- ~~Mobile/responsive layout (sidebar needs touch treatment)~~ — REMOVED 2026-08-08 (CEO: not needed)
- Export/import conversations
- ~~Search across threads~~ — DONE: shipped M18–M20 (AC-63..71); the sidebar search matches
  BOTH thread titles and message content (`src/static/threads.js:374-377`), hit
  navigation in the open thread. Retired 2026-08-08 after implementing
  verification (the PRD/test-assertion view understated the shipped scope).
- ~~Multi-model comparison (side-by-side responses)~~ — REMOVED 2026-08-08 (CEO: not needed)

### ~~Candidate: file-granular changed_tests refinement~~ — RETIRED 2026-08-14
**Priority:** ~~P3~~ — superseded by D-140's function-granular DELTA producer.
`refreeze_delta.py` now records only living tests whose executable function AST
changed; comments, whitespace, formatting, and leading function/module
docstrings do not enter `changed_tests`. New or modified tests must also carry
an owning-file pin at freeze time. Infrastructure changes outside test
functions remain conservatively file-scoped because fixtures, imports, helpers,
and constants can change every test's meaning. Revisit only if measured runs
show that this intentional safety fallback creates material recurring cost.

---

## Icebox (someday/maybe)

- Image/file upload support
- Voice input
- Conversation branching / forking

---

## Completed

| Task | Completed | Notes |
|------|-----------|-------|
| Contracts entry→file pin (D-120) | 2026-08-06 | v83 backfill of routes/schemas/errors + v86 ui testid pins; DELTA-v85 onward carries the pinned baseline |
| M1 — Echo Chat | 2026-07-03 | Canned responses, full stack wired |
| M2 — Live LLM Proxy | 2026-07-04 | Real HTTP call to local LLM endpoint |
| M3 — Streaming (SSE) | (see git) | Token-by-token SSE |
| M4 — Conversation History | (see git) | Full context sent to LLM |
| M5 — Nemotron mgmt/routing | (see git) | Load/unload + endpoint routing |
| M6 — Multichat threads | (see git) | In-memory threads, spec v9 |
| M7 — UI tests + fixes | 2026-07-09 | spec v14, 67/67 |
| M8 — Persistence | 2026-07-10 | spec v17, CEO-accepted |
| M9 — Polish Sweep | 2026-07-12 | spec v19, CEO-accepted (crash fix, formatting) |
| M10-M11 — Live-fix features | 2026-07-12 | Markdown, 10 themes, thread mgmt, stop, status, system prompt, focus mode, bubble chrome, cursor, column, throttle |
| M12 — Ratify the Sprint | 2026-07-12 | spec v26, 101/101 green |
| app.js split | 2026-07-12 | markdown.js + threads.js + app.js (live-fix) |
