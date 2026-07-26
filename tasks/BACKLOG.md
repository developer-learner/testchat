# BACKLOG.md — Task Queue

> Ordered by priority. Top = next up.
> When starting a task, move it to CURRENT.md and expand it into a full spec.

---

## Up Next

### Pinned-but-unloaded model offers no way to load it
**Priority:** P1
**Why:** A thread persists its selected model (`thread.model` in
`data/threads.json`), and on restore the dropdown shows that model as the
current value. The load-confirm modal fires ONLY from
`modelSelect.addEventListener('change', …)` (`src/static/app.js`) — so
re-picking the already-displayed model generates no `change` event, no modal,
and no load. The model is selected, unloaded, and unloadable from that thread.
The only escape is picking a different model and switching back, which nothing
in the UI suggests.
**Not an edge case:** 34 of 42 threads currently carry a pinned model.
Observed 2026-07-25 — thread id=1 (31 msgs) pins `deepseek-v4-flash`; after
any restart it renders selected-but-unloaded with no load path, and the app
appears simply broken. Compounds with the unload defect below: after a restart
the catalog can also report a stale `loaded: true`, so the selector shows a
model that is neither loadable nor genuinely loaded.
**What:** provide a load affordance that does not depend on a `change` event —
e.g. a load button beside the selector, enabled whenever the current selection
has `dataset.loaded === 'false'`; or run the load-confirm flow on thread
restore when the restored model is unloaded. Either way the invariant is:
*if the selected model is not loaded, there is always a visible way to load
it.*
**Rough size:** Spec/test + `src/static/app.js`

### Script-model unload silently fails after any app restart
**Priority:** P1
**Why:** `unload_script_model` (`src/services/models.py:151`) terminates only a
process it holds a live `subprocess.Popen` handle for. Those handles live in
`_script_processes`, an in-memory dict (`:50`), so they die with the app. After
any restart the spawned server is orphaned (PPID 1) but still running — and
unload returns `{"status": "unloaded"}` regardless, having killed nothing.
`is_script_model_loaded()` probes over HTTP, so the catalog keeps correctly
reporting `loaded: true`. Permanent desync, no recovery path from the UI.
Two consequences beyond the stuck button:
(a) the model holds its RAM and its port indefinitely;
(b) `_unload_other_script_models` (`:109`) — the RAM mutual-exclusion
guarantee — detects the stale model correctly, calls unload, receives a
confident success, and loads the second model on top of it. Two large script
models resident at once, silently. This is a plausible path to the
"RAM full, cannot load a model" symptom.
**Trigger is routine, not exotic:** the documented run command is
`uvicorn src.main:app --reload`, which restarts the worker on every file save.
Editing any source file while a script model is loaded orphans it.
**Repro (verified 2026-07-25):** load `deepseek-v4-flash` → confirm
`ds4-server` is a child of the app process → restart the app → catalog still
`loaded: true` → `POST .../unload` → `{"status": "unloaded"}` → process still
alive. Control: identical load/unload *without* a restart works correctly —
process gone, port freed, catalog accurate. So the defect is specifically the
lost handle, not the unload path itself.
**What:** (1) persist the PID at load time instead of relying solely on the
in-memory handle; (2) on unload with no handle, fall back to that PID,
verifying process identity before signalling; (3) stop returning `unloaded`
unconditionally — re-probe `ready_url` after the kill attempt and report
honestly when the server is still up. (3) is the cheapest and highest-value
piece, converts a silent lie into a visible error, and can ship alone.
**Rough size:** Spec/test + `src/services/models.py`

### Startup guard — refuse to bind a port a script model claims
**Priority:** P2
**Why:** The app's default port (8000) is the same port `DS4_URL` points at,
and the app spawns that server itself — so following the documented quick
start guaranteed a collision on the first DeepSeek load. Two failure shapes,
both verified 2026-07-25: bound to `127.0.0.1:8000`, `ds4-server` cannot bind
(`EADDRINUSE`) and the load dies after the full 180s ready timeout; bound to
`0.0.0.0:8000`, both binds succeed, the more-specific address wins, and the
model server silently inherits `localhost:8000` — the open page keeps
rendering while every `/api/v1/*` call returns `unknown endpoint`, killing a
live chat with no symptom pointing at the port. Docs now warn (`4bdaa90`),
but nothing enforces it.
**What:** at startup, compare the bind port against every `SCRIPT_MODELS`
entry's configured port and refuse to start with a named error. Optionally
warn on a `0.0.0.0` bind, which is what turns the collision silent rather
than loud.
**Rough size:** Spec/test + `src/main.py`

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
