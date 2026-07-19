# BACKLOG.md — Task Queue

> Ordered by priority. Top = next up.
> When starting a task, move it to CURRENT.md and expand it into a full spec.

---

## Up Next

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

### M13 — app.js module split (spec backfill)
**Priority:** P2
**Why:** Split already landed as live-fix (markdown.js, threads.js, app.js);
needs TPM spec coverage if pipeline work resumes
**Rough size:** Spec-only (code done)

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
