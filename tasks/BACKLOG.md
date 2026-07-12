# BACKLOG.md — Task Queue

> Ordered by priority. Top = next up.
> When starting a task, move it to CURRENT.md and expand it into a full spec.

---

## Up Next

### M9 close-out — CEO demo acceptance (D-44)
**Priority:** P1
**Why:** All three M9 items landed, [success] spec v19; only the CEO gate remains
**Rough size:** Demo session

---

## Later

- Nemotron unload macOS crash dialog — deferred from M9 by frozen PRD v19;
  needs live diagnosis with the real model + CEO (SIGINT fix `1d7defd` was
  the intended fix; verify it live).
- ~M10: split app.js by feature when growth warrants (chat/threads-ui/persistence)

---

## Icebox (someday/maybe)

- Multiple chat sessions with persistence
- Model selection dropdown
- System prompt customization

---

## Completed

| Task | Completed | Notes |
|------|-----------|-------|
| M1 — Echo Chat | 2026-07-03 | Canned responses, full stack wired |
| M2 — Live LLM Proxy | 2026-07-04 | Real HTTP call to local LLM endpoint, env-based config, error fallback |
| M3 — Streaming (SSE) | (see git) | Token-by-token SSE with token/think/done/error events |
| M4 — Conversation History | (see git) | Full context sent to LLM |
| M5 — Nemotron mgmt/routing | (see git) | Load/unload + endpoint routing |
| M6 — Multichat threads | (see git) | In-memory threads, spec v9 [success] |
| M7 — (spec v14) | 2026-07-09 | `2391c38` [success], 67/67 incl. UI tests |
| M8 — Persistence (spec v17) | 2026-07-10 | `a7f00a7` [success], CEO-accepted 2026-07-10 |
D-59 candidate: validator auto-maps attributed node-ids (D-57 part 2) — needs CEO sign-off (Rule 3)
