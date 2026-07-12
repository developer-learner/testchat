# CURRENT.md — Session Notes

> This is the human-facing status page, NOT the spec. The PRD, ERD, contracts
> and test suite live frozen in `scripts/.approved/` + `tests/` and change
> only via `scripts/refreeze.sh` (D-31). Update this file at the start and end
> of every working session; halt notes (Rule 4) land here.

---

## Active Feature

**Feature:** M9 — Polish Sweep (three deterministic fixes)
**Frozen spec version:** v19 (frozen)
**Orchestrator state:** done ([success] spec v19, commit `07bb7d0`)
**Branch:** `main`

---

## Latest Results

**M9 (Polish Sweep)** — all three in-scope items landed and green:
- AC-39/40 — `NEMOTRON_URL` env config, default `http://localhost:8600` (`src/services/models.py`, T1 `4c774e9`).
- AC-41 — failed replies retain the user's message (`src/static/app.js`, `da19ff8`, CEO-delegated).
- AC-42 — "thinking..." placeholder while no visible answer text has rendered (`src/static/app.js`, `da19ff8`).

Deferred by the frozen PRD (NOT in M9): the macOS "Python quit unexpectedly"
dialog on Nemotron unload — needs live diagnosis on the real model with the
CEO; SIGINT shutdown (`1d7defd`) was already the intended fix.

CEO demo acceptance pending (D-44). See PRD v19 CEO demo script.

---

## Escalations In Flight

None.

---

## Notes / Context

Milestone plan:
- M1: Echo chat — ✅ done
- M2: Live LLM integration — ✅ done
- M3: Streaming (SSE) — token-by-token response — ✅ done
- M4: Conversation history — full context sent to LLM — ✅ done
- M5: Nemotron model management + routing — ✅ done
- M6: Multichat in-memory threads — ✅ built (CEO acceptance pending)

---

## Definition of Done (per feature)

Mechanical checks:

- Full frozen suite green (`scripts/orchestrate.sh` exit 0)
- `docs/ARCHITECTURE.md` updated if structure changed
- `docs/DECISIONS.md` updated if a non-obvious choice was made
- No linter errors (`ruff check src/`)

The one judgment check (D-44 — the CEO's gate, never skipped or delegated):

- **CEO has used the running prototype and accepted the milestone.**
  "Tests green" means built-as-specified; only this means built-right.
  Record the acceptance here with a date.

Then: branch merged to main; entry moved to `BACKLOG.md` completed table

## Results

Full frozen TPM suite green against spec v3. Feature built and validated.

## Results

Full frozen TPM suite green against spec v5. Feature built and validated.

## Results

Full frozen TPM suite green against spec v7. Feature built and validated.

## Results

Full frozen TPM suite green against spec v9. Feature built and validated.

## 2026-07-09 — M7 landed outside-band (CEO-approved), D-59 pending
- v14 frozen; T1/T2 green in-pipeline; T3 full-file coder attempt deleted 119
  lines (browser oracle caught it at T4's gate); halt stands per protocol.
- Working app.js landed via CEO-approved commit: coder-authored anchored edit
  blocks, fail-closed apply, 67/67 in repo (incl. 7 UI tests). Repo tree is
  demo-ready. No [success] tag — that awaits the in-band re-run.
- Tomorrow: D-59 template work (coder reply = anchored edit blocks + applier
  in run_coder; strip_think_tags hazard; anchor rules in coder.md), CEO
  sign-off, sync, re-run M7 for in-band [success]. Then CEO demo (D-44).

## Results

Full frozen TPM suite green against spec v14. Feature built and validated.

## Results

Full frozen TPM suite green against spec v17. Feature built and validated.

## 2026-07-09 (eve) — HANDOFF: state + operational knowledge (LLM-agnostic)
Read CLAUDE.md, docs/CONDUCTOR-ROLE.md, docs/DECISIONS.md (template repo,
D-55..D-60) before acting. Derive state from git, never from this note.

State: M7 (`2391c38` v14) and M8 persistence (`a7f00a7` v17) both [success],
78/78 frozen tests, zero post-success hand-fixes either milestone. M8 CEO
demo acceptance (D-44) still pending. App runs on :8080 locally (port 8000
must stay free for Nemotron — known collision, see M9).

M9 queue (next milestone, TPM cycle, deliberately small): (1) Nemotron
unload shows a macOS "Python quit unexpectedly" dialog — an old uncommitted
hand-fix that evaporated; fix + guard this time. (2) Port-8000 collision:
NEMOTRON_BASE_URL hardcoded (src/services/models.py) vs app's default port.
(3) Error-path history loss: messages only commit on 'done' — a stream
error drops the user's message and can lock an empty thread. (4) UX: a
'thinking...' placeholder in the reply bubble while a model reasons silently
(qwen thinks for minutes; an empty bubble reads as frozen — CEO-reported
2026-07-10). M8 was CEO-accepted 2026-07-10. Later (~M10):
split app.js by feature when growth warrants (chat/threads-ui/persistence).

Operational knowledge, hard-won:
- Approvals: the CEO granted session-scoped delegation for refreeze/sync
  gates on 2026-07-08/09. This does NOT carry over — re-ask the CEO.
- Syncing template→child: after ANY sync, verify by content/hash (grep a
  known new string in a synced file), never trust exit status — two silent
  no-op syncs happened here. docs/ never syncs (manifest has no docs/
  entries); child-visible law must ride in .opencode/prompts/*.
- EM thrash pattern: if plan revisions oscillate between two errors, check
  the spec for UNSATISFIABLE constraints first (v15/v16: a task with no
  mapped tests AND no smoke_check is illegal by construction).
- Pipeline runs ONLY in the VM: `limactl shell dev-vm`, repo at the same
  absolute path. Model mapping: ~/.config/sw-dev-blueprint/models.env (VM
  copy is separate from host!) — CEO-owned, agents never write it.
- Chat-UI relays are lossy for code containing literal think tags; use the
  raw llm-call path or concatenation-constructed tags (D-59 notes).

## Results

Full frozen TPM suite green against spec v19. Feature built and validated.

## 2026-07-11 — Session: M9 status verified, CURRENT.md brought current
- Verified from git + host test run (74/74 non-UI frozen tests pass; UI tests
  need playwright, VM-only): M9's three in-scope items all landed, [success]
  spec v19 tagged. No code work remained — the handoff's 4th queue item
  (unload crash dialog) is explicitly deferred by the frozen PRD.
- Fixed stale Active Feature header (was still M6/v9).
- Remaining before M9 closes: CEO demo acceptance (D-44).

## 2026-07-11 (eve) — Live CEO session: crash root-caused, 3 UI live-fixes
- Nemotron crash dialog ROOT-CAUSED from the .ips report: SIGSEGV in MLX's
  CompilerCache C++ destructor during interpreter teardown — crash is on
  clean EXIT, not in signal handling (why the SIGINT fix "didn't work").
  Fix: SIGINT/SIGTERM -> os._exit(0) prepended to ~/nemotron-vmlx.py
  (host-owned, backup at ~/nemotron-vmlx.py.bak). First unload of an
  already-running old process still shows the dialog once.
- Live-fixes (CEO-delegated): 32fa2b4 pre-wrap bubbles; 2ece022 minimal
  markdown rendering (escape-first) in reply bubbles; b07882d no-cache on
  / and /static (stale-CSS/JS bites every UI change). 74/74 backend green.
- CAVEAT: the 7 frozen Playwright UI tests did NOT run (host has no
  playwright; VM-only). renderThink output changed (adds strong/em/code,
  '- '->'•'), which could touch text assertions — re-run the full suite in
  the VM before any new [success] claim.

## 2026-07-11 (late) — Crash fix v2: VERIFIED FIXED (2 live cycles)
- CORRECTION: the first os._exit patch (signal handlers only) did NOT hold —
  a post-patch process (launched 21:46) still segfaulted. Cause: vmlx_engine
  runs uvicorn.run(), whose signal capture can supersede wrapper handlers.
- v2 patch in ~/nemotron-vmlx.py, three layers: SIGINT/SIGTERM handlers +
  uvicorn.run wrapped in try/finally os._exit(0) + atexit os._exit(0). Every
  exit path now bypasses the segfaulting MLX CompilerCache teardown.
- Verified live via the app UI: two full Load->ready->Unload cycles, process
  exits ~1s, ZERO new DiagnosticReports, no Problem Reporter dialog.
  (All 4 of today's crashed PIDs had the app as parent — the load-timeout
  SIGINT path crashed the same way; it is now silent too.)

## 2026-07-12 — Live CEO session #2: M10-class features landed outside-band
- 5a80fa6 markdown block renderer (fenced code + copy, headings, nested
  lists, quotes, hr, links), thread rename/delete (persisted), auto-retitle
  of generic titles from first reply, Send->Stop (abort keeps partial reply
  + user msg). 2281b2a styles + matrix sharpness (glow 2px, 15px antialiased).
- All verified live in-browser: block-by-block render check, rename/delete
  round-trip through PUT /threads, stop mid-nemotron-stream (partial kept,
  no error bubble). Backend suite 74/74 after every commit.
- NOTE: these were CEO-directed live fixes; the TPM has no ACs for them yet.
  Next TPM cycle should backfill spec coverage (or fold into M10 split).
  Frozen Playwright suite still needs a VM re-run.

## 2026-07-12 (cont) — Design evolution items 1-4 landed + verified live
- 6cf6b10 /api/v1/status (stdlib RAM/RSS probes) + HistoryEntry ts/model
  (optional, defaulted; chat.py still forwards role/content only).
- c251263 centered 52rem reading column, per-bubble hover chrome (copy /
  delete-pair / time+model via pseudo-content — textContent unchanged),
  blinking stream cursor, footer status strip (model, RAM, nemotron RSS,
  live + avg tok/s).
- Verified live: column gutters symmetric at 1400px; cursor present during
  stream, gone on done; strip showed nemotron 43.1 GB RSS and 42 tok/s live.
  74/74 backend green; ruff clean. Test exchanges removed from data/.
- Still owed: TPM spec backfill for all session-2 features; VM Playwright run.

## 2026-07-12 (later) — Debt: VM suite GREEN; system-prompt feature landed
- DEBT ITEM 1 CLEARED: full frozen suite run in VM sandbox (sandbox-run.sh,
  podman, --network none): 84/84 PASSED incl. Playwright UI tests — all
  session-1/2 UI changes (markdown, themes, chrome, strip) survived frozen
  assertions untouched.
- DEBT ITEM 2 (TPM spec backfill for live-fix features) still open — needs
  the CEO's TPM web-chat cycle; conductor can produce the tpm-pack bundle.
- New feature (CEO-requested): app-wide system prompt. ea96321 settings
  service + API (env var stays authoritative when present — frozen chat
  tests pin that, incl. empty-string); f893262 gear-button modal UI + fix
  for [hidden] defeated by display:flex (invisible overlay ate clicks).
  Verified live: saved "pirate" prompt -> nemotron replied "ARRR Hello";
  cleared afterwards. 74/74 host, ruff clean.
