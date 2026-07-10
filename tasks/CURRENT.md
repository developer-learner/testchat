# CURRENT.md — Session Notes

> This is the human-facing status page, NOT the spec. The PRD, ERD, contracts
> and test suite live frozen in `scripts/.approved/` + `tests/` and change
> only via `scripts/refreeze.sh` (D-31). Update this file at the start and end
> of every working session; halt notes (Rule 4) land here.

---

## Active Feature

**Feature:** M6 — Multichat (in-memory threads)
**Frozen spec version:** v9 (frozen)
**Orchestrator state:** done (60/60 tests green)
**Branch:** `main`

---

## Latest Results

**M6 (Multichat in-memory threads)** — built and validated. All 60 frozen tests pass. Frontend-only milestone.
- `src/static/index.html` — sidebar with thread list, New Chat button, per-thread message history/model/lock state, background streaming on thread switch, auto-title from first message.

CEO acceptance pending (D-44). See PRD CEO demo script for manual verification steps.

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
