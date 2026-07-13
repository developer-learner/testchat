# BACKLOG.md — Task Queue

> Ordered by priority. Top = next up.
> When starting a task, move it to CURRENT.md and expand it into a full spec.

---

## Up Next

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
