# ERD — testchat M2: Live LLM Proxy (erd_version 2)

## What changes M1 → M2
- **Removed:** `src/services/echo.py` and entry point `src.services.echo:echo`.
- **Added:** `src/services/llm.py` — the proxy service, entry point
  `src.services.llm:generate_reply`.
- **Modified:** `src/api/chat.py` — route handler now calls `generate_reply`
  instead of the echo service.
- **Unchanged (carried forward from frozen v1, excluded from build inventory):**
  `src/main.py`, `src/static/index.html`, `GET /`, and the `ChatRequest` /
  `ChatResponse` shapes.

## File inventory (M2 build)
- `src/services/llm.py`  — new
- `src/api/chat.py`      — rewritten to call the LLM service

## Data models
- **ChatRequest** — `{ "message": str }` (unchanged).
- **ChatResponse** — `{ "reply": str }` (unchanged).
- **generate_reply** — `generate_reply(message: str) -> str`. Reads config from
  the environment, POSTs an OpenAI-compatible chat-completions request to
  `LLM_ENDPOINT`, and returns either the model's content or `FALLBACK_REPLY`.
  Synchronous (see C-4).
- **Upstream request body** —
  `{ "model": <LLM_MODEL>,
     "messages": ([{"role":"system","content":<LLM_SYSTEM_PROMPT>}] if set else [])
                 + [{"role":"user","content":<message>}],
     "stream": false }`
- **Upstream success extraction** — `data["choices"][0]["message"]["content"]`;
  missing/empty ⇒ `FALLBACK_REPLY`.
- **FALLBACK_REPLY** — the fixed string in PRD → Fixed constants, defined once in
  `src/services/llm.py` and imported nowhere else.

## Configuration (read at request time — see C-3)
| Env var                | Default                                          |
|------------------------|--------------------------------------------------|
| `LLM_ENDPOINT`         | `http://localhost:1234/v1/chat/completions`      |
| `LLM_MODEL`            | `local-model`                                    |
| `LLM_SYSTEM_PROMPT`    | `` (empty ⇒ no system message)                   |
| `LLM_TIMEOUT_SECONDS`  | `120`                                            |

## Key flows
1. **Send message.** Page JS → `POST /api/v1/chat` with `{"message": <text>}`
   → `chat.py` validates against `ChatRequest` → calls
   `generate_reply(message)` → `llm.py` reads env, builds the OpenAI body,
   POSTs to `LLM_ENDPOINT` (non-streaming, `LLM_TIMEOUT_SECONDS`) → on success
   returns content, on any failure returns `FALLBACK_REPLY` → `chat.py` returns
   `{"reply": <that string>}` → page appends a bubble.
2. **Page load.** Unchanged from v1 (`GET /` serves `index.html`).

## Constraints (implementation-affecting, non-optional)
- **C-1 (default endpoint).** When `LLM_ENDPOINT` is unset, the service targets
  `http://localhost:1234/v1/chat/completions`. This literal default is a
  live-demo requirement, recorded here rather than as an AC because it cannot be
  observed at the test surface without binding the dev's real `:1234` port.
- **C-2 (failure containment).** Every upstream failure mode — connection error,
  timeout, non-2xx, and malformed/empty content — maps to `FALLBACK_REPLY` at
  HTTP 200. No exception escapes `generate_reply`; the route never returns 5xx.
- **C-3 (late-bound config).** Config is resolved from `os.environ` inside
  `generate_reply` on each call, not at module import, so the operator and the
  tests can point `LLM_ENDPOINT` at different upstreams without re-import.
- **C-4 (sync).** `generate_reply` and the `/api/v1/chat` handler are
  synchronous for M2 (FastAPI runs the handler in a threadpool); an outbound
  sync `httpx.Client` call is used. Async is deferred.
- **C-5 (surface).** The only importable symbols the suite may use from `src` are
  the locked entry points `src.main:app` and `src.services.llm:generate_reply`.
  The only HTTP route the suite exercises is `POST /api/v1/chat` (INV-4).
- **C-6 (layering).** Proxy logic lives only in `llm.py`; `chat.py` imports and
  calls it and owns no LLM/HTTP logic of its own.

## Oracle Mapping (AC → test node)
- AC-1  → `tests/test_llm_service.py::test_success_returns_model_content`,
          `tests/test_chat_api.py::test_chat_returns_model_reply`
- AC-2  → `tests/test_llm_service.py::test_request_carries_model_and_user_message`
- AC-3  → `tests/test_llm_service.py::test_system_prompt_included_when_set`
- AC-4  → `tests/test_llm_service.py::test_system_prompt_omitted_when_empty`
- AC-5  → `tests/test_llm_service.py::test_request_is_non_streaming`
- AC-6  → `tests/test_llm_service.py::test_config_read_at_call_time`
- AC-7  → `tests/test_llm_service.py::test_connection_error_returns_fallback`,
          `tests/test_chat_api.py::test_chat_upstream_failure_returns_fallback_200`
- AC-8  → `tests/test_llm_service.py::test_non_2xx_returns_fallback`
- AC-9  → `tests/test_llm_service.py::test_malformed_response_returns_fallback`,
          `tests/test_llm_service.py::test_empty_content_returns_fallback`
- AC-10 → `tests/test_llm_service.py::test_timeout_returns_fallback`
- AC-11 → `tests/test_chat_api.py::test_chat_missing_message_is_422`
- AC-12 → `tests/test_chat_api.py::test_chat_no_longer_echoes`

## Milestone Justification (D-46)
This is one milestone, not several. The change is a single seam — the source of
`reply` — behind an unchanged, already-frozen contract. It ends at a concrete
CEO-checkable point (D-44): send a message, see a real model reply; kill the
model, see the fallback. Splitting it (e.g. "wire the client" then "add failure
handling") would burn freeze/accept cycles on states the CEO cannot evaluate
independently — a proxy with no failure handling isn't demoable, and the page is
untouched so there is no frontend sub-milestone.

## Test dependencies
`pytest` with `fastapi.testclient.TestClient` (needs `fastapi`, `httpx`) and
`pytest-httpserver` (a real localhost HTTP server used as the fake OpenAI
upstream, addressed via `LLM_ENDPOINT`). Tests observe the system only through
the locked entry points and the `LLM_*` configuration surface; the fake upstream
is controlled purely through `LLM_ENDPOINT`, so no test knows how the request is
made. Test-infra imports (`fastapi.testclient`, `pytest_httpserver`) are not
`src` observations and do not affect INV-4.
