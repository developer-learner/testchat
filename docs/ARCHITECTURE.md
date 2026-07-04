# ARCHITECTURE.md — System Design

> Living document. Update when structure changes.
> LLMs read this to understand how the system fits together.

---

## System Overview

testchat is a FastAPI application that serves a static HTML chat page and exposes a single API endpoint for sending messages. In M1, the backend returns a canned echo response. In later milestones, it will proxy messages to a configurable OpenAI-compatible local LLM endpoint.

---

## Data Models

### ChatRequest

| Field | Type | Notes |
|-------|------|-------|
| message | str | The user's chat message |

### ChatResponse

| Field | Type | Notes |
|-------|------|-------|
| reply | str | The assistant's response |

No database. No persistence. All state is in-browser only.

---

## API Structure

```
GET    /                        HTML chat page (static)
POST   /api/v1/chat             send a message, get a reply
```

---

## Key Flows

### M1: Echo Chat

1. User opens browser to `/`
2. Static HTML chat page loads
3. User types a message and clicks send
4. JavaScript POSTs to `/api/v1/chat` with `{"message": "..."}`
5. Backend returns `{"reply": "Echo: ..."}`
6. JavaScript appends the reply as a chat bubble

---

## External Services

| Service | Purpose | Notes |
|---------|---------|-------|
| Local LLM endpoint | Chat completions (M2+) | Any OpenAI-compatible server, configurable base URL via env var |

---

## Infrastructure

```
Local
├── App server:    uvicorn (single process)
├── Database:      None
├── Cache:         None
└── Static files:  Served by FastAPI (src/static/)
```

---

## Known Constraints

- No database — all conversation state lives in the browser's JS memory
- Single user, single conversation at a time
- No auth — this is a local-only tool
- Static HTML served by FastAPI, not a JS framework build step
