# PRD — testchat, Milestone M1: Echo Chat

**Spec version:** v1 (initial freeze)
**Owner:** TPM
**Status:** proposed — freezes on operator `refreeze.sh` approval

## What

A minimal browser chat backed by FastAPI. The server serves a single chat page
at `GET /`. The user types a message; the page POSTs it as JSON to
`POST /api/v1/chat`; the backend returns the same text with an `Echo: ` prefix;
the page renders the reply as a chat bubble. There is no LLM and no model of any
kind in M1 — the "intelligence" is a literal echo. This milestone exists to
stand up the full request → response → render loop end to end, so later
milestones can replace the echo with real logic behind a stable contract.

## Milestone framing (D-46 / D-44)

M1 is deliberately the whole echo loop across all four source files rather than a
backend-only or page-only fragment, because only the complete loop is
CEO-checkable. Splitting it would spend a freeze/accept cycle on a half that
cannot be demonstrated. Because M1 includes a UI, acceptance is the CEO **using
the prototype**: loading `/` in a browser, sending a message, and seeing the
`Echo: <message>` bubble appear. The automated suite below pins the backend
contract and the page-to-API wiring; the live-use check pins that the bubble
actually renders in the browser.

## Acceptance Criteria (EARS — one clause per test)

- **AC-1** — WHEN a client sends `GET /`, the system SHALL respond with status
  `200` and a `Content-Type` of `text/html`.
  *(test: `tests/test_page.py::test_root_serves_html_page`)*

- **AC-2** — WHEN a client sends `GET /`, the returned HTML SHALL reference the
  path `/api/v1/chat`, i.e. the served page is wired to the API endpoint it
  posts to.
  *(test: `tests/test_page.py::test_page_wires_chat_endpoint`)*

- **AC-3** — WHEN a client sends `POST /api/v1/chat` with JSON body
  `{"message": "hello"}`, the system SHALL respond with status `200` and JSON
  body `{"reply": "Echo: hello"}`.
  *(test: `tests/test_chat_route.py::test_chat_echoes_message`)*

- **AC-4** — WHEN a client sends `POST /api/v1/chat` with JSON body
  `{"message": ""}`, the system SHALL respond with status `200` and JSON body
  `{"reply": "Echo: "}`.
  *(test: `tests/test_chat_route.py::test_chat_empty_message_echoed`)*

- **AC-5** — IF a client sends `POST /api/v1/chat` with a JSON body that omits
  the `message` field, THEN the system SHALL respond with status `422`.
  *(test: `tests/test_chat_route.py::test_chat_missing_message_is_validation_error`)*

- **AC-6** — WHEN `echo(message)` is called with a non-empty string, it SHALL
  return the literal `Echo: ` immediately followed by `message`.
  *(test: `tests/test_echo_service.py::test_echo_prefixes_message`)*

- **AC-7** — WHEN `echo("")` is called, it SHALL return `"Echo: "`.
  *(test: `tests/test_echo_service.py::test_echo_empty_message`)*

- **AC-8** — WHEN `echo(message)` is called, it SHALL return `message` verbatim
  after the prefix, with no trimming, escaping, or other alteration, including
  for non-ASCII and markup characters.
  *(test: `tests/test_echo_service.py::test_echo_is_verbatim`)*

## Flagged Assumptions (authorized on approval)

- **FA-1** — An empty message (`""`) is a valid input and echoes as `"Echo: "`;
  it is not a validation error. (Pinned by AC-4/AC-7.)
- **FA-2** — The message is echoed verbatim on the backend: no trimming, no
  length cap, no HTML-escaping. Escaping for safe display is a frontend concern.
  (Pinned by AC-8.)
- **FA-3** — A missing `message` field yields `422` (FastAPI/Pydantic default).
  Only the missing-field case is specified; malformed/non-string payloads are
  out of scope for M1. (Pinned by AC-5.)
- **FA-4** — `src/static/index.html` is self-contained (inline CSS/JS) and is
  served by `src/main.py`; no separate static-asset mount exists in M1.
- **FA-5** — Request and response media type for `/api/v1/chat` is
  `application/json`.

## Out of Scope (M1)

- Any LLM, model, or non-echo reply logic.
- Conversation history, state, or persistence of any kind.
- Streaming / server-sent responses.
- Authentication, rate limiting, multi-user, sessions.
- Validation of non-string `message` payloads (only the missing-field case is
  pinned).
- Visual styling beyond a minimal readable chat layout.
