# ERD — testchat M3: Streaming LLM Proxy (erd_version 3)

## What changes M2 → M3
- **Modified:** `src/services/llm.py` — `generate_reply` (single-shot)
  replaced by `stream_reply`, a generator over upstream content increments;
  upstream request now sets `"stream": true` and parses SSE-framed chunks.
- **Modified:** `src/api/chat.py` — route handler now returns a
  `StreamingResponse` over `text/event-stream`, framing `stream_reply`'s
  output as `token`/`done`/`error` SSE events instead of a JSON body.
- **Modified:** `src/static/index.html` — fetch/render logic switches from
  awaiting one JSON response to reading `response.body` as a stream, parsing
  SSE frames, and appending `token` content live; handles `done`/`error`.
- **Unchanged:** `src/main.py`, `GET /`, `ChatRequest` schema, 422 validation
  behavior.
- **Removed:** `generate_reply` entry point (M2) — no longer exported;
  nothing else imports it (A6).

## File inventory (M3 build)
- `src/services/llm.py`       — modified
- `src/api/chat.py`           — modified
- `src/static/index.html`     — modified

## Data models
- **ChatRequest** — `{ "message": str }` (unchanged).
- **stream_reply** — `stream_reply(message: str) -> Iterator[StreamChunk]`.
  Reads config from the environment on each call (C-3, carried from M2).
  Yields chunks as they're derived from the upstream; raises nothing across
  the generator boundary — every failure mode is represented as a chunk
  value, not an exception, so `chat.py` never needs a try/except around
  iteration.
- **StreamChunk** (internal, not on the wire) — a small tagged union
  `llm.py` yields to `chat.py`:
  - `("token", content: str)` — one non-empty content increment.
  - `("done",)` — clean end of stream, only after ≥1 `("token", ...)`.
  - `("error",)` — any failure, pre-stream, mid-stream, or a clean-but-empty
    completion (AC-7). `chat.py` supplies `FALLBACK_REPLY` as the message
    text; `llm.py` does not pass failure detail upward.
- **SSE wire frames** (what `chat.py` writes to the client) — per PRD → SSE
  wire contract:
  - `event: token` / `data: {"content": <str>}`
  - `event: done` / `data: {}`
  - `event: error` / `data: {"message": <FALLBACK_REPLY>}`
- **Upstream request body** —
  `{ "model": <LLM_MODEL>,
     "messages": ([{"role":"system","content":<LLM_SYSTEM_PROMPT>}] if set else [])
                 + [{"role":"user","content":<message>}],
     "stream": true }`
- **Upstream chunk shape (OpenAI-compatible SSE)** — lines of
  `data: <json>`, each JSON having `choices[0].delta.content` (may be
  absent/empty on some chunks), terminated by a literal `data: [DONE]` line.
  `llm.py` extracts non-empty `delta.content` values as `token` chunks. A
  well-formed `data: [DONE]` line is the *only* trigger for `done` — and
  only if at least one `token` chunk preceded it (AC-6/AC-7). Anything
  else that ends the stream — EOF without `[DONE]`, a malformed/unparseable
  `data:` line, or a connection-level error — is `error`, regardless of how
  many `token` chunks preceded it (AC-12).
- **FALLBACK_REPLY** — unchanged fixed string, still defined once in
  `src/services/llm.py`, used only by `chat.py` when framing an
  `("error",)` chunk.

## Configuration (read at request time — see C-3)
| Env var                | Default                                          | M3 semantics change                         |
|------------------------|---------------------------------------------------|---------------------------------------------|
| `LLM_ENDPOINT`         | `http://localhost:1234/v1/chat/completions`      | none                                          |
| `LLM_MODEL`            | `local-model`                                    | none                                          |
| `LLM_SYSTEM_PROMPT`    | `` (empty ⇒ no system message)                   | none                                          |
| `LLM_TIMEOUT_SECONDS`  | `120`                                             | now bounds time-to-first-byte only (A2)     |

## Key flows
1. **Send message (happy path).** Page JS → `fetch POST /api/v1/chat` with
   `{"message": <text>}` → `chat.py` validates against `ChatRequest` → opens
   a `StreamingResponse`, calls `stream_reply(message)` → `llm.py` reads
   env, builds the upstream body with `"stream": true`, opens a streaming
   POST to `LLM_ENDPOINT` with connect/first-byte bound by
   `LLM_TIMEOUT_SECONDS` → for each upstream chunk with non-empty
   `delta.content`, yields `("token", content)` → `chat.py` writes
   `event: token` immediately per yield (no buffering) → on upstream
   `[DONE]`, `llm.py` yields `("done",)` if ≥1 token was already yielded,
   else `("error",)` (AC-7) → `chat.py` writes the corresponding terminal
   event and ends the response → page appends each `token`'s content live,
   finalizes on `done`.
2. **Pre-stream failure.** Connect fails, non-2xx, or no first byte within
   `LLM_TIMEOUT_SECONDS` → `llm.py` yields `("error",)` with no prior
   `token` yields → `chat.py` writes `event: error` (message =
   `FALLBACK_REPLY`) and ends → page shows only the fallback text.
3. **Mid-stream failure.** One or more `token` chunks already yielded, then
   upstream drops or sends a malformed/unparseable line → `llm.py` yields
   `("error",)` → `chat.py` writes `event: error` and ends → page appends
   `FALLBACK_REPLY` after whatever already rendered (A5).
4. **Empty completion.** Upstream sends `[DONE]` having never carried
   non-empty content → `llm.py` yields only `("error",)`, never `("done",)`
   — mirrors M2's empty-content fallback rule (AC-7).
5. **Page load.** Unchanged from v1/v2 (`GET /` serves `index.html`).
6. **Missing `message`.** Unchanged — FastAPI/pydantic validation returns
   422 before `chat.py`'s handler body runs; no stream is opened.

## Constraints (implementation-affecting, non-optional)
- **C-1 (default endpoint).** Carried from M2 — `LLM_ENDPOINT` defaults to
  `http://localhost:1234/v1/chat/completions`.
- **C-2 (failure containment, streaming form).** Every upstream failure
  mode — connect error, timeout-to-first-byte, non-2xx, mid-stream drop,
  malformed chunk, or a clean-but-empty completion — surfaces as exactly one
  `error` SSE event, never as a change in HTTP status (status is already
  committed as 200 by the time most failures are knowable) and never as an
  unhandled exception reaching Starlette. No exception escapes `stream_reply`
  or the route.
- **C-3 (late-bound config).** Carried from M2 — config resolved from
  `os.environ` inside `stream_reply` on each call, not at import.
- **C-4 (sync generator, threaded).** `stream_reply` is a synchronous
  generator using a sync `httpx.Client` streaming call; FastAPI/Starlette
  iterates it via its threadpool-wrapping `StreamingResponse` support,
  consistent with M2's C-4 sync posture. Async is still deferred.
- **C-5 (surface).** The only importable symbols the suite may use from
  `src` are `src.main:app` and `src.services.llm:stream_reply`. The only
  HTTP route exercised is `POST /api/v1/chat` (INV-4).
- **C-6 (layering).** `llm.py` owns upstream protocol, chunk parsing, and
  failure classification (yields the `StreamChunk` union only — never
  SSE-formatted text). `chat.py` owns SSE framing (turning `StreamChunk`
  values into `event:`/`data:` bytes) and owns no upstream/HTTP-to-LLM
  logic. Mirrors M2's C-6 split one layer up the stack.
- **C-7 (one terminal event, no empty success).** Exactly one of `done` or
  `error` is emitted per request, always last; `token` events, if any, only
  ever precede it. `done` requires at least one prior `token` — a clean
  `[DONE]` with zero tokens is `error`, not `done` (AC-7).

## Oracle Mapping (AC → test node)
- AC-1  → `tests/test_chat_api.py::test_chat_opens_event_stream_200`
- AC-2  → `tests/test_llm_service.py::test_request_carries_model_user_message_and_stream_true`
- AC-3  → `tests/test_llm_service.py::test_system_prompt_included_when_set`
- AC-4  → `tests/test_llm_service.py::test_system_prompt_omitted_when_empty`
- AC-5  → `tests/test_llm_service.py::test_content_chunks_yielded_as_tokens_in_order`,
          `tests/test_chat_api.py::test_chat_streams_token_events_in_order`
- AC-6  → `tests/test_llm_service.py::test_clean_completion_yields_done`,
          `tests/test_chat_api.py::test_chat_emits_done_after_tokens`
- AC-7  → `tests/test_llm_service.py::test_empty_stream_yields_error_not_done`
- AC-8  → `tests/test_llm_service.py::test_config_read_at_call_time`
- AC-9  → `tests/test_llm_service.py::test_connection_error_yields_error_with_no_tokens`,
          `tests/test_chat_api.py::test_chat_connection_error_emits_error_only`
- AC-10 → `tests/test_llm_service.py::test_non_2xx_yields_error_with_no_tokens`
- AC-11 → `tests/test_llm_service.py::test_timeout_to_first_byte_yields_error`
- AC-12 → `tests/test_llm_service.py::test_mid_stream_drop_yields_error_after_tokens`,
          `tests/test_chat_api.py::test_chat_mid_stream_failure_emits_error_after_tokens`
- AC-13 → `tests/test_chat_api.py::test_chat_missing_message_is_422_no_stream`
- AC-14, AC-15, AC-16 → CEO Demo Script (frontend, no automated harness —
  consistent with M1/M2 treatment of `index.html`)

## Milestone Justification (D-46)
One milestone. The seam is the same one M2 built (`reply` production), now
made incremental; splitting backend-streaming from frontend-rendering would
produce an interim state — SSE events with no UI consuming them — that the
CEO can't observe or accept (D-44 requires a checkable point, and once a UI
exists, checking means using it). The failure-containment redesign (C-2) is
inseparable from the backend half: it can't be called done without the same
request lifecycle the frontend triggers.

## Test dependencies
`pytest`, `fastapi.testclient.TestClient` (`client.stream(...)` context
manager for consuming chunked/streaming responses in tests), `pytest-httpserver`
(extended to serve a fake SSE-chunked upstream — a static multi-line body for
happy-path/malformed-data cases, and a slow `respond_with_handler` for the
timeout case). Same INV-4 posture as M2: test-infra imports are not `src`
observations and do not affect the surface gate.
