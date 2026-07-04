# PRD — testchat M3: Streaming LLM Proxy (SSE)

## Milestone
M3 (v3). Replace the non-streaming JSON reply from M2 with a token-by-token
Server-Sent Events stream on the same `POST /api/v1/chat` route. The upstream
request switches to `"stream": true`. The page (`src/static/index.html`) is
updated in this milestone to consume the stream and render tokens live —
the one deliberate exception to M1/M2's "frontend unchanged" invariant, made
necessary by the feature itself. No conversation history (M4). No
reconnection/resume of dropped streams. Sized as one milestone — see
ERD → Milestone Justification. Done means: send a message, watch the reply
appear incrementally as the model generates it (not one blob); kill the model
mid-reply, see the partial text plus a fallback message appended, page
doesn't error.

## What
`POST /api/v1/chat` with `{"message": "<text>"}`:
- Validates the body (422 on missing `message`, unchanged).
- Builds an OpenAI-compatible chat-completions request with `"stream": true`,
  using the same `messages` construction rule as M2 (system prompt prepended
  WHERE `LLM_SYSTEM_PROMPT` is non-empty, user message last).
- Opens the upstream stream and responds to the client HTTP 200,
  `Content-Type: text/event-stream`, before any content is known.
- Forwards each upstream content increment as a `token` SSE event, in order.
- On clean completion with at least one token emitted, sends one terminal
  `done` event and closes. A clean completion that never emitted any content
  is treated as a failure, not an empty success (see AC-7) — mirrors M2's
  "empty content ⇒ fallback" rule.
- On any other failure — pre-stream (unreachable, non-2xx, no first byte
  within `LLM_TIMEOUT_SECONDS`) or mid-stream (connection drop, malformed
  chunk) — emits one `error` event carrying `FALLBACK_REPLY` and closes. No
  retry.
- The M2 JSON response shape (`{"reply": str}`) is retired on this route;
  nothing else in the repo depends on it.

`GET /` is unchanged. `src/static/index.html` changes only its fetch/render
logic: it opens the POST via `fetch()`, reads the response body as a stream,
and appends `token` text to the active bubble live; on `done` it finalizes
the bubble; on `error` it appends the error message to whatever's already
rendered (empty string if nothing streamed yet) and stops the loading
indicator.

## Fixed constants
- **FALLBACK_REPLY** = `"The language model is currently unavailable. Please try again in a moment."`
  (unchanged from M2, now delivered via an `error` event instead of a 200
  JSON body).

## SSE wire contract
Each frame is standard SSE (`event: <name>\ndata: <json>\n\n`):
- `event: token`, `data: {"content": "<text>"}` — one per non-empty increment.
- `event: done`, `data: {}` — terminal, success path only, requires ≥1 prior
  `token` event (AC-7).
- `event: error`, `data: {"message": "<text>"}` — terminal, failure path
  only. Mutually exclusive with `done` on a given request; `token` events
  may precede either.

## Acceptance Criteria (EARS notation)
Backend clauses are pytest-verified; frontend clauses are CEO-demo-verified
(D-44 — no JS harness exists in this project).

- **AC-1:** WHEN a client POSTs to `/api/v1/chat` with a valid
  `{"message": <text>}` body, THE SYSTEM SHALL respond HTTP 200 with
  `Content-Type: text/event-stream`, opened before any upstream content is
  known.
- **AC-2:** WHEN handling a chat request, THE SYSTEM SHALL POST to
  `LLM_ENDPOINT` a JSON body whose `model` equals `LLM_MODEL`, whose `stream`
  is `true`, and whose `messages` contains the user's message as the final
  `user`-role message.
- **AC-3:** WHERE `LLM_SYSTEM_PROMPT` is non-empty, THE SYSTEM SHALL include
  it as the first `messages` element with role `system`.
- **AC-4:** WHERE `LLM_SYSTEM_PROMPT` is empty or unset, THE SYSTEM SHALL NOT
  include any `system`-role message.
- **AC-5:** WHEN the upstream emits a chunk containing non-empty delta
  content, THE SYSTEM SHALL forward it to the client as a `token` SSE event
  whose `content` equals that increment, in arrival order.
- **AC-6:** WHEN the upstream stream ends cleanly after at least one token
  was emitted, THE SYSTEM SHALL send exactly one terminal `done` event and
  close the connection.
- **AC-7:** IF the upstream stream ends cleanly having emitted zero token
  events, THEN THE SYSTEM SHALL emit a single `error` event (message =
  `FALLBACK_REPLY`) instead of `done`.
- **AC-8:** THE SYSTEM SHALL resolve `LLM_ENDPOINT`, `LLM_MODEL`,
  `LLM_SYSTEM_PROMPT`, and `LLM_TIMEOUT_SECONDS` from the environment at
  request-handling time, not at import time.
- **AC-9:** IF the configured endpoint is unreachable, THEN THE SYSTEM SHALL
  emit a single `error` event with `message` = `FALLBACK_REPLY`, preceded by
  no `token` events, and close.
- **AC-10:** IF the upstream returns a non-2xx status before streaming
  begins, THEN THE SYSTEM SHALL emit a single `error` event with `message` =
  `FALLBACK_REPLY`, preceded by no `token` events, and close.
- **AC-11:** IF the upstream sends no first byte within
  `LLM_TIMEOUT_SECONDS`, THEN THE SYSTEM SHALL abort and emit a single
  `error` event with `message` = `FALLBACK_REPLY`, preceded by no `token`
  events, and close.
- **AC-12:** IF the upstream connection drops or sends malformed/unparseable
  data after one or more `token` events have already been emitted, THEN THE
  SYSTEM SHALL emit an `error` event with `message` = `FALLBACK_REPLY` and
  close, without retry.
- **AC-13:** WHEN a client POSTs to `/api/v1/chat` with a body missing the
  `message` field, THE SYSTEM SHALL respond HTTP 422 without opening an SSE
  stream (unchanged from M1/M2).
- **AC-14 (frontend, demo):** WHEN the page receives a `token` event, THE
  SYSTEM SHALL append its `content` to the active reply bubble, in receipt
  order.
- **AC-15 (frontend, demo):** WHEN the page receives a `done` event, THE
  SYSTEM SHALL stop the loading indicator and finalize the bubble.
- **AC-16 (frontend, demo):** WHEN the page receives an `error` event, THE
  SYSTEM SHALL append its `message` to whatever is already rendered in the
  active bubble (empty string if no tokens preceded it) and stop the loading
  indicator.

## Out of Scope
- Multi-turn conversation history (M4).
- Automatic reconnection/resume of an interrupted stream — a dropped
  connection ends the turn; the user re-sends to retry.
- Graceful mid-stream cancellation on client disconnect (tab close,
  navigation) — the server-side request runs to completion regardless;
  resource cleanup on disconnect is deferred.
- Per-chunk idle timeout — `LLM_TIMEOUT_SECONDS` bounds time-to-first-byte
  only (see A2); a stalled-but-connected stream isn't separately bounded
  this milestone.
- Retries, backoff, circuit-breaking, rate limiting.
- Auth to the LLM endpoint beyond M2's existing posture.
- Any change to `GET /`, the request shape `{"message": str}`, or page
  markup/layout beyond the fetch/render logic.

## Flagged Assumptions (CEO sign-off before freeze)
- **A1 (load-bearing, CEO-confirmed):** `POST /api/v1/chat` is replaced in
  place — the M2 JSON response shape is retired on this route, not preserved
  on a parallel endpoint.
- **A2 (load-bearing):** `LLM_TIMEOUT_SECONDS` is redefined from "total
  request timeout" (M2) to "time-to-first-byte" (M3) — same env var name,
  new meaning.
- **A3:** `src/static/index.html` re-enters the build inventory this
  milestone — the one deliberate exception to M1/M2's "frontend unchanged"
  invariant, required by the feature itself. Only fetch/render JS changes;
  markup/layout untouched.
- **A4:** The backend re-frames the upstream's OpenAI-style delta JSON into
  the minimal `token`/`done`/`error` contract above, rather than passing
  upstream's raw chunks through — decouples the frontend from the upstream's
  wire format.
- **A5 (CEO-confirmed):** On a mid-stream error, the fallback message is
  appended after any partial text already rendered, not a replacement of it.
- **A6:** M2's `generate_reply` entry point is removed and replaced by a
  streaming equivalent (`stream_reply`, see ERD). Confirm nothing else in
  the repo imports the old signature.
- **A7:** No new env vars introduced; the existing four (`LLM_ENDPOINT`,
  `LLM_MODEL`, `LLM_SYSTEM_PROMPT`, `LLM_TIMEOUT_SECONDS`) suffice.
- **A8:** A clean upstream completion that emits zero content (straight to
  `[DONE]`, nothing sent) is treated as a failure (`error` + `FALLBACK_REPLY`),
  not rendered as an empty successful bubble — mirrors M2's empty-content
  fallback rule under the new streaming shape.

## CEO Demo Script
1. Start LM Studio (or any OpenAI-compatible server) on `:1234` with a
   streaming-capable model loaded.
2. Run the app, open the page, send a message with a longer expected reply —
   confirm text appears incrementally, not as one blob.
3. Mid-reply, stop the model server — confirm the bubble keeps whatever
   streamed so far, the fallback message is appended after it, and the page
   doesn't error.
4. Stop the model server before sending — send a message — confirm the
   bubble shows only the fallback message (no partial content).
