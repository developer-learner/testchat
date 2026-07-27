# BACKLOG.md — Task Queue

> Ordered by priority. Top = next up.
> When starting a task, move it to CURRENT.md and expand it into a full spec.

---

## Up Next

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

### Run the frozen suite unprivileged in the sandbox
**Priority:** P1
**Why:** The container runs as root; the app runs as a normal user on macOS.
M29 shipped `psutil.net_connections()` (module-level), which needs root on
macOS: it passed 153/153 in the container while 5 tests failed on the host. A
green oracle over a broken production path — caught only because the host run
was done manually. The per-process form (`psutil.process_iter()` →
`proc.net_connections()`) works in both and is what landed.
**What:** Drop root in `sandbox-run.sh` so capability-dependent code cannot pass
in the sandbox and fail in production. Interim rule until then: never declare
green without a host run.
**Rough size:** `sandbox-run.sh` / `Containerfile` + a DECISIONS entry

### Spec lint, reverse direction — live tests vs NEW ACs
**Priority:** P1
**Why:** The existing lint checks staged tests against live ACs. v58 passed it
and still shipped a contradiction in the other direction: the carried-forward
`test_load_nemotron_expands_script_path` monkeypatches `httpx.get` to return
200 for **every** URL, which makes the *other* script model read as loaded, so
new AC-104 correctly refuses to spawn and `Popen` is never called — while the
test asserts it was. Unsatisfiable alongside AC-104; cost a full escalation
cycle and the v59 refreeze to fix.
**What:** (a) diff live carried-forward tests against the ACs a delta ADDS, not
only staged tests against live ACs; (b) treat a mock that answers every URL as a
lint failure — it encodes "the whole world is ready" and silently couples
unrelated subsystems.
**Rough size:** `check-test-surface.py` or a new refreeze lint

### Halve the full-suite wall clock (freeze-time floor)
**Priority:** P2
**Why:** The Playwright suite takes ~4.5 min per full run on the host (176
tests at v65) and grows with every milestone. Post-D-86/D-87, freeze
discipline runs the staged suite before every refreeze, so suite runtime is
now the floor on every spec change — v65's staging spent ~9 of its ~30
minutes inside two full runs.
**What:** (a) `pytest-xdist` sharding for the browser tests (each test is
already isolated per-context), and/or (b) a changed-tests-first ordering so
a red staged suite fails in seconds. Tests-lane infra: `conftest.py` +
possibly CI config, so it lands via a refreeze.
**Rough size:** conftest fixture scoping audit + one dependency addition

### Fold `mypy` into the sandbox run
**Priority:** P2
**Why:** CI's type-check is a gate nothing local exercises — the sandbox runs
pytest and ruff only. M29's `psutil` addition passed two full platform runs at
153/153 and still broke CI on `Library stubs not installed for "psutil"`,
costing a red build and a follow-up commit (`types-psutil`, `0eb1d38`).
**What:** Add `mypy --explicit-package-bases src/` to the sandbox acceptance so
CI-only gates stop existing.
**Rough size:** `sandbox-run.sh` + `orchestrate.sh` acceptance

### `em.md` — test node-ids must be copied verbatim
**Priority:** P2
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

### AC-15 disposition + AC-101 — a pinned unloaded model must be loadable
**Priority:** P1
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

### Spec lint at refreeze — post-conditions for state-changing ACs
**Priority:** P1
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

### AC-48 audit — Stop-mid-stream is an unaudited cancellation AC
**Priority:** P3
**Why:** The 2026-07-25 lint recovered 77 of ~100 AC statements; 23 have no
surviving PRD text. All 23 are UI/theme/markdown/rename **except AC-48**
(deliberately slow stream so a test can click Stop mid-reply), which is a
cancellation operation — the same class as the failing process-lifecycle ACs
and never checked for a post-condition.
**What:** Recover AC-48's text and apply the §5.1 lint.
**Rough size:** Spec review only

### AC-42 flake hardening — test_thinking_placeholder_shows_then_clears
**Priority:** P1
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

### AC-47 recut — thread-delete confirm off native window.confirm
**Priority:** P2 (bundle with the AC-42 refreeze above)
**Why:** CEO wants all confirms themed (2026-07-19). Message-pair delete
now uses the themed delete-confirm-modal (live-fix), but thread delete
must stay `window.confirm` because frozen AC-47
(`test_thread_delete_removes_thread`) drives it via `page.once("dialog")`
— a custom modal leaves the thread undeleted and fails the suite.
**What:** TPM recuts AC-47 to click the modal's confirm button; then
`deleteThread` switches to the same `confirmDelete()` helper in
threads.js (one-line swap, code path already exists).
**Rough size:** Spec/test + one-line code change

### M13 — app.js module split (spec backfill)
**Priority:** P2
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

---

## Later

- Mobile/responsive layout (sidebar needs touch treatment)
- Export/import conversations
- Search across threads
- Multi-model comparison (side-by-side responses)

---

## Icebox (someday/maybe)

- Image/file upload support
- Voice input
- Conversation branching / forking

---

## Completed

| Task | Completed | Notes |
|------|-----------|-------|
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
