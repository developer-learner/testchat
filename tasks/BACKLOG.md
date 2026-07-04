# BACKLOG.md — Task Queue

> Ordered by priority. Top = next up.
> When starting a task, move it to CURRENT.md and expand it into a full spec.

---

## Up Next

### M3 — Streaming (SSE)
**Priority:** P1
**Why:** Token-by-token response streaming for real-time chat feel
**Rough size:** Medium
**Depends on:** M2 (done)

### M4 — Conversation History
**Priority:** P2
**Why:** Send full conversation context to LLM, not just last message
**Rough size:** Small
**Depends on:** M2 (done)

---

## Later

(empty)

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
