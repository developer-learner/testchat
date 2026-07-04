# BACKLOG.md — Task Queue

> Ordered by priority. Top = next up.
> When starting a task, move it to CURRENT.md and expand it into a full spec.

---

## Up Next

### M2 — Live LLM Integration
**Priority:** P1
**Why:** Replace echo stub with real HTTP call to operator's local LLM endpoint
**Rough size:** Small
**Depends on:** M1

### M3 — Streaming (SSE)
**Priority:** P1
**Why:** Token-by-token response streaming for real-time chat feel
**Rough size:** Medium
**Depends on:** M2

### M4 — Conversation History
**Priority:** P2
**Why:** Send full conversation context to LLM, not just last message
**Rough size:** Small
**Depends on:** M2

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
