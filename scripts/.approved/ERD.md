ERD — testchat M4: Conversation History (erd_version 4)
What changes M3 → M4

Modified: src/api/chat.py — ChatRequest pydantic model gains an
optional history field (list of HistoryEntry, default []);
HistoryEntry model added (role: Literal["user","assistant"],
content: str). Route handler extracts validated history and passes it
to stream_reply. SSE framing logic unchanged.
Modified: src/services/llm.py — stream_reply gains a history
parameter (sequence of role/content dicts, default empty). Messages-array
construction now inserts history entries between the system prompt and
the current user message. Streaming, chunk parsing, failure
classification, and the StreamChunk yield protocol are unchanged.
Modified: src/static/index.html — JS maintains an in-memory
conversation array. On a successful turn (done), both the user message
and accumulated assistant response are appended. On a failed turn
(error), neither is added. The array is sent as history in every
POST. Page reload resets it to [].
Unchanged: src/main.py, GET /, SSE wire format
(token/done/error), StreamChunk tagged union, FALLBACK_REPLY
constant, 422 validation for missing message, all failure-handling
paths.
Removed: nothing.

File inventory (M4 build)

src/services/llm.py       — modified
src/api/chat.py           — modified
src/static/index.html     — modified

Data models

ChatRequest — { "message": str, "history": list[HistoryEntry] = [] }
(extended from M3). Pydantic validates: message required string;
history optional, each entry validated as HistoryEntry.
HistoryEntry (pydantic model in chat.py) —
{ "role": Literal["user", "assistant"], "content": str }. An entry
with role outside the enum, or missing role/content, triggers
pydantic's 422 before the handler body runs.
stream_reply —
stream_reply(message: str, history: Sequence[dict[str, str]] = ()) -> Iterator[StreamChunk].
chat.py converts validated HistoryEntry objects to plain dicts before
calling. history defaults to empty (M3-compatible). Reads config from
os.environ on each call (C-3, carried). Yields StreamChunk values
only — no exceptions across the generator boundary (carried from M3).
StreamChunk — unchanged from M3:

("token", content: str) — one non-empty content increment.
("done",) — clean end, requires ≥1 prior ("token", ...).
("error",) — any failure or clean-but-empty completion.


SSE wire frames — unchanged from M3.
Upstream request body —
{ "model": <LLM_MODEL>,    "messages": ([{"role":"system","content":<LLM_SYSTEM_PROMPT>}] if set else [])                + [{"role": h["role"], "content": h["content"]} for h in history]                + [{"role":"user","content":<message>}],    "stream": true }
Upstream chunk shape — unchanged from M3. OpenAI-compatible SSE with
choices[0].delta.content, terminated by data: [DONE].
FALLBACK_REPLY — unchanged, still defined once in src/services/llm.py.

Configuration (read at request time — C-3)
Env varDefaultM4 changeLLM_ENDPOINThttp://localhost:1234/v1/chat/completionsnoneLLM_MODELlocal-modelnoneLLM_SYSTEM_PROMPT`` (empty ⇒ no system message)noneLLM_TIMEOUT_SECONDS120none
No new env vars introduced.
Key flows

Multi-turn happy path. Page JS → user sends message → JS builds
{"message": <text>, "history": [<prior turns>]} → fetch POST →
chat.py validates ChatRequest (including HistoryEntry list) →
opens StreamingResponse, calls
stream_reply(message, history=[...dicts...]) → llm.py reads env,
constructs messages array as [system if set] + history + [user msg],
opens streaming POST with "stream": true → yields ("token", ...)
chunks → chat.py writes event: token per yield → on [DONE],
yields ("done",) → chat.py writes event: done → page
accumulates tokens, on done stores user msg + assistant response in
conversation array for next turn.
First message (no history). Client sends
{"message": <text>} or {"message": <text>, "history": []} →
identical to M3 flow (empty history produces same messages array).
Failed turn (error, pre-stream or mid-stream). Same failure
mechanics as M3. Page receives error event, displays it, but does NOT
add the turn to the conversation array — next request's history
excludes the failed exchange.
Page reload. JS conversation array is reset to []. Next message
sends empty history — model has no prior context.
Validation failure. Invalid history entry (bad role, missing
field) → pydantic 422, no stream opened — same pattern as missing
message.
All other flows (page load via GET /, empty completion AC-7,
pre-stream failures AC-9/10/11) — unchanged from M3.

Constraints
M3 constraints C-1 through C-7 carry forward unchanged. Additions:

C-8 (history passthrough). stream_reply places history dicts
directly into the upstream messages array in the position specified by
the ERD data model (after system prompt, before current user message).
It does not validate, filter, or transform history entries —
validation is chat.py's responsibility via pydantic, completed before
stream_reply is called.
C-9 (validation boundary). All history validation (role enum,
required fields) is handled by pydantic in chat.py. stream_reply
trusts its input — it receives only entries that survived validation.
This keeps llm.py free of request-validation concerns (C-6 layering
preserved).

Oracle Mapping (AC → test node)
Carried from M3 (all remain in force, same test nodes)

M3-AC-1  → tests/test_chat_api.py::test_chat_opens_event_stream_200
M3-AC-2  → tests/test_llm_service.py::test_request_carries_model_user_message_and_stream_true
M3-AC-3  → tests/test_llm_service.py::test_system_prompt_included_when_set
M3-AC-4  → tests/test_llm_service.py::test_system_prompt_omitted_when_empty
M3-AC-5  → tests/test_llm_service.py::test_content_chunks_yielded_as_tokens_in_order,
tests/test_chat_api.py::test_chat_streams_token_events_in_order
M3-AC-6  → tests/test_llm_service.py::test_clean_completion_yields_done,
tests/test_chat_api.py::test_chat_emits_done_after_tokens
M3-AC-7  → tests/test_llm_service.py::test_empty_stream_yields_error_not_done
M3-AC-8  → tests/test_llm_service.py::test_config_read_at_call_time
M3-AC-9  → tests/test_llm_service.py::test_connection_error_yields_error_with_no_tokens,
tests/test_chat_api.py::test_chat_connection_error_emits_error_only
M3-AC-10 → tests/test_llm_service.py::test_non_2xx_yields_error_with_no_tokens
M3-AC-11 → tests/test_llm_service.py::test_timeout_to_first_byte_yields_error
M3-AC-12 → tests/test_llm_service.py::test_mid_stream_drop_yields_error_after_tokens,
tests/test_chat_api.py::test_chat_mid_stream_failure_emits_error_after_tokens
M3-AC-13 → tests/test_chat_api.py::test_chat_missing_message_is_422_no_stream

M4-specific (new)

AC-1 → tests/test_llm_service.py::test_history_entries_in_upstream_messages
AC-2 → tests/test_llm_service.py::test_history_with_system_prompt_ordering
AC-3 → tests/test_llm_service.py::test_history_without_system_prompt_ordering
AC-4 → tests/test_llm_service.py::test_empty_history_matches_m3_behavior
AC-5 → tests/test_chat_api.py::test_chat_invalid_history_role_is_422
AC-6 → tests/test_chat_api.py::test_chat_history_missing_fields_is_422
AC-7 → (meta — covered by the full carried-from-M3 suite above)
AC-8, AC-9, AC-10, AC-11 → CEO Demo Script (frontend, no automated
harness — consistent with M1/M2/M3 treatment of index.html)

Milestone Justification (D-46)
One milestone. The backend change (inserting history into the upstream
messages array) is unobservable without the frontend change (tracking turns
and sending them). Splitting them produces an interim state the CEO cannot
check — a modified request schema with no client exercising it (D-44).
The feature is small enough to fit a single freeze cycle: the streaming
mechanics, failure handling, and SSE framing are unchanged; the delta is
the messages-array construction and the JS conversation tracking.
Test dependencies
pytest, fastapi.testclient.TestClient, pytest-httpserver — unchanged
from M3. Same INV-4 posture: test-infra imports (pytest_httpserver,
werkzeug, json, time, os) are not src observations and do not
affect the surface gate.
