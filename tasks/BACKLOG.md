# BACKLOG.md — Task Queue

> Ordered by priority. Top = next up.
> When starting a task, move it to CURRENT.md and expand it into a full spec.

---

## Up Next

### AC-95′/AC-96′ recut — "unloaded" must mean the process is gone
**Priority:** P0
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
`docs/POSTMORTEM-2026-07-25-unload-spec-lint.md` §6.
**Rough size:** Spec + test + `services/models.py`

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
