# PRD — testchat M2: Live LLM Proxy

## Milestone
M2 (v2). Replace the echo service with a live proxy to a local,
OpenAI-compatible chat-completions endpoint. The page, the route, and the
request/response shapes are unchanged from M1 — only the source of `reply`
changes: from `"Echo: <text>"` to a real model completion. Endpoint, model
name, and system prompt are configurable via environment. No streaming (M3).
No conversation history (M4). Sized as one milestone — see ERD → Milestone
Justification. Done means: with a model served on the configured endpoint,
open the page, send a message, and see a real model reply bubble (not an echo).

## What
The existing FastAPI app `testchat`, with its chat service replaced so that
`POST /api/v1/chat` with `{"message": "<text>"}`:
- Builds an OpenAI-compatible chat-completions request from the message plus an
  optional configured system prompt.
- POSTs it (non-streaming) to the endpoint in `LLM_ENDPOINT`.
- Returns `{"reply": "<model content>"}` on success.
- Returns `{"reply": "<fixed fallback string>"}`, still HTTP 200, on any upstream
  failure (unreachable, timeout, non-2xx, malformed/empty content), so the
  frozen M1 page keeps rendering a bubble.
`GET /` and the page are carried forward from the frozen v1 unchanged.

## Fixed constants
- **FALLBACK_REPLY** = `"The language model is currently unavailable. Please try again in a moment."`
  (pinned so failure paths are testable; may be promoted to an env var later — see A8.)

## Acceptance Criteria (EARS notation)
Each clause is one observable test; test mapping in ERD → Oracle Mapping.

- **AC-1:** WHEN a client POSTs to `/api/v1/chat` with `{"message": <text>}` AND
  the configured endpoint returns a successful completion, THE SYSTEM SHALL
  respond HTTP 200 with body `{"reply": <choices[0].message.content>}`.
- **AC-2:** WHEN handling a chat request, THE SYSTEM SHALL POST to `LLM_ENDPOINT`
  a JSON body whose `model` equals `LLM_MODEL` and whose `messages` contains the
  user's message as the final `user`-role message.
- **AC-3:** WHERE `LLM_SYSTEM_PROMPT` is non-empty, THE SYSTEM SHALL include, as
  the first element of `messages`, a `system`-role message whose content equals
  `LLM_SYSTEM_PROMPT`.
- **AC-4:** WHERE `LLM_SYSTEM_PROMPT` is empty or unset, THE SYSTEM SHALL NOT
  include any `system`-role message in the upstream request.
- **AC-5:** WHEN handling a chat request, THE SYSTEM SHALL request a
  non-streaming completion (`stream` absent or `false`).
- **AC-6:** THE SYSTEM SHALL resolve `LLM_ENDPOINT`, `LLM_MODEL`, and
  `LLM_SYSTEM_PROMPT` from the environment at request-handling time, not at
  import time.
- **AC-7:** IF the configured endpoint is unreachable, THEN THE SYSTEM SHALL
  respond HTTP 200 with body `{"reply": FALLBACK_REPLY}`.
- **AC-8:** IF the endpoint returns a non-2xx status, THEN THE SYSTEM SHALL
  respond HTTP 200 with body `{"reply": FALLBACK_REPLY}`.
- **AC-9:** IF the response lacks `choices[0].message.content` or that content is
  empty, THEN THE SYSTEM SHALL respond HTTP 200 with body `{"reply": FALLBACK_REPLY}`.
- **AC-10:** IF the upstream does not respond within `LLM_TIMEOUT_SECONDS`, THEN
  THE SYSTEM SHALL abort the request and respond HTTP 200 with body
  `{"reply": FALLBACK_REPLY}`.
- **AC-11:** WHEN a client POSTs to `/api/v1/chat` with a body missing the
  `message` field, THE SYSTEM SHALL respond HTTP 422 (unchanged from M1).
- **AC-12:** WHEN the endpoint returns a completion, THE SYSTEM SHALL return that
  content verbatim as `reply` with no `"Echo: "` prefix (echo behavior removed).

## Out of Scope
- Streaming / token-by-token rendering (M3).
- Conversation history / multi-turn context (M4) — each request sends exactly
  one user message (plus optional system prompt).
- Retries, backoff, circuit-breaking, rate limiting.
- Auth to the LLM endpoint beyond an optional bearer token (see A9); LM Studio
  ignores it locally.
- Any change to `src/static/index.html`, `GET /`, or the response shape.
- Configurable temperature / max_tokens / other sampling params.

## Flagged Assumptions (CEO sign-off before freeze)
- **A1 (load-bearing):** Upstream failures return HTTP 200 + `FALLBACK_REPLY`,
  not a 5xx. Preserves the frozen page and the `ChatResponse` shape. Overriding
  this rewrites AC-7..AC-10 and their tests and implies a frontend change.
- **A2:** Env var names are `LLM_ENDPOINT`, `LLM_MODEL`, `LLM_SYSTEM_PROMPT`,
  `LLM_TIMEOUT_SECONDS`. Downstream `.env`/run config depends on these.
- **A3:** Defaults — `LLM_ENDPOINT` → `http://localhost:1234/v1/chat/completions`;
  `LLM_MODEL` → `"local-model"` (LM Studio accepts arbitrary); `LLM_SYSTEM_PROMPT`
  → `""`; `LLM_TIMEOUT_SECONDS` → `120`.
- **A4:** System prompt is omitted when empty (vs. always sending a system
  message). Default: omit.
- **A5:** Empty user message is forwarded to the model as-is (carries M1's
  accept-empty behavior), not short-circuited.
- **A6:** `src/services/echo.py` is removed and replaced by `src/services/llm.py`;
  `src/main.py` and `src/static/index.html` carry forward unchanged and are
  intentionally excluded from the M2 build inventory. Confirm the pipeline can
  express a file removal + retire the old `src.services.echo` entry point;
  otherwise I repurpose `echo.py` in place instead.
- **A7:** `httpx` (already present as a test dep via `TestClient`) becomes a
  runtime dependency; `pytest-httpserver` is added as a test dependency for the
  fake upstream. Confirm dependency additions.
- **A8:** `FALLBACK_REPLY` text is pinned as above for testability. Confirm the
  wording, or whether it should be an env var.
- **A9 (blueprint-version check):** If this blueprint version expects, as of M2,
  a TPM-authored `smoke_check` oracle and/or consult-outcome logging hooks in the
  freeze, give me the format and I'll add them — I left them out rather than
  guess a format that would fail install. Also: an optional `LLM_API_KEY` bearer
  header — include now or defer? Left out by default.

## CEO Demo Script
1. Start LM Studio (or any OpenAI-compatible server) on `:1234` with a model
   loaded; set `LLM_MODEL` to that model.
2. Run the app, open the page, send "hello" — confirm a real model reply bubble
   appears (not `Echo: hello`).
3. Stop the model server; send another message — confirm the bubble reads the
   fallback message and the page does not error.
