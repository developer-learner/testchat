# ERD — testchat M1 (Echo Chat)

**erd_version:** 1

## File inventory

Exactly four source files (one implementation task each, per the plan gate):

| File | Responsibility |
|------|----------------|
| `src/services/echo.py` | Pure echo logic. Exposes `echo(message: str) -> str` returning `"Echo: " + message`. No FastAPI, no I/O, no import of the web layer. This is the only place echo logic lives. |
| `src/api/chat.py` | The chat API surface. Defines a FastAPI `APIRouter` with `POST /api/v1/chat`, validates the request body against `ChatRequest`, calls `echo()` from the service, and returns `ChatResponse`. Imports `echo` from `src.services.echo`; contains no echo logic itself. |
| `src/main.py` | Application composition root. Creates the FastAPI app, includes the chat router from `src.api.chat`, and serves the chat page at `GET /`. Exposes the ASGI app as module-level symbol `app` (`src.main:app`). |
| `src/static/index.html` | The chat page: self-contained HTML with inline CSS and JS. Renders an input, POSTs `{"message": ...}` to `/api/v1/chat` on submit, and appends the returned `reply` as a chat bubble. Must contain the literal endpoint path `/api/v1/chat`. |

## Data models

- **ChatRequest** — `{ "message": str }`. `message` is required.
- **ChatResponse** — `{ "reply": str }`.
- **echo** — `echo(message: str) -> str`, returns `f"Echo: {message}"`. Verbatim
  (no trim/escape/cap).

## Key flows

1. **Page load.** Browser → `GET /` → `main.py` returns the contents of
   `src/static/index.html` with `Content-Type: text/html`.
2. **Send message.** Page JS → `POST /api/v1/chat` with `{"message": <text>}`
   → `chat.py` validates → `echo.py` produces `"Echo: <text>"` →
   `chat.py` returns `{"reply": "Echo: <text>"}` → page JS appends a bubble.

## Constraints (implementation-affecting, non-optional)

- **C-1 (path resolution).** `main.py` must resolve `src/static/index.html`
  relative to its own module location, not the process working directory, so the
  page serves correctly regardless of where the server is launched from.
- **C-2 (layering).** Echo logic exists only in `echo.py`. `chat.py` imports it;
  `main.py` wires routers and the page. No duplication of the `Echo: ` prefix
  outside `echo.py`.
- **C-3 (surface).** The only importable symbols the test suite may use are those
  declared in `contracts.entry_points` (`src.main:app`, `src.services.echo:echo`).
  The only HTTP routes are those in `contracts.routes` (`GET /`,
  `POST /api/v1/chat`).
- **C-4 (validation).** A missing `message` field must produce HTTP `422`
  (satisfied naturally by binding the body to `ChatRequest`).

## Test dependencies

The frozen suite runs under `pytest` using `fastapi.testclient.TestClient`
(requires `fastapi` and `httpx` available in the test environment). Tests import
only from the locked entry points and exercise only the locked routes.
