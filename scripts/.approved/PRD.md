PRD — testchat M4: Conversation History
Milestone
M4 (v4). Add multi-turn conversation context so the LLM sees the full
exchange, not just the last message. The existing POST /api/v1/chat
request body is extended with an optional history array — the prior turns
the client has accumulated — which the backend inserts into the upstream
messages array between the system prompt and the current user message. The
frontend (src/static/index.html) tracks successful turns in memory and
sends them on each subsequent request. No server-side storage, no
persistence across page reloads. Done means: send a message, get a reply,
send a follow-up referencing the first exchange, and the model's reply
demonstrates awareness of the prior context.
What
POST /api/v1/chat with {"message": "<text>", "history": [...]}:

history is an ordered array of prior conversation turns, each
{"role": "user"|"assistant", "content": "<text>"}. Optional; defaults
to [] when absent, producing M3-identical behavior.
Validates the body: 422 on missing message (unchanged), and 422 on
any history entry with a role other than "user" or "assistant",
or missing role/content.
Builds the upstream messages array as:
[system prompt if LLM_SYSTEM_PROMPT is non-empty]
+ history entries in order
+ [current user message]
— then streams the response identically to M3 (SSE framing, failure
containment, terminal events all unchanged).

Frontend changes (in src/static/index.html):

Maintains an in-memory array of conversation turns.
On a successful turn (done event received): stores the user's message
and the accumulated assistant response as history entries.
On a failed turn (error event received): does NOT add either the user
message or the partial/fallback response to the history array. The
display is unchanged from M3 (error text is visible to the user), but the
failed turn is excluded from future LLM context.
Sends the accumulated history array with every POST /api/v1/chat.
Page refresh clears the array — conversation starts fresh.

All M3 streaming mechanics are preserved: SSE wire contract
(token/done/error), failure containment (C-2), env-var resolution at
request time (C-3), sync generator posture (C-4), layering (C-6), one
terminal event rule (C-7). The only surface change to the route is the
expanded request body.
Fixed constants

FALLBACK_REPLY = "The language model is currently unavailable. Please try again in a moment."
(unchanged — still delivered via an error SSE event).

SSE wire contract
Unchanged from M3:

event: token, data: {"content": "<text>"} — one per non-empty increment.
event: done, data: {} — terminal, success path, requires ≥1 prior token.
event: error, data: {"message": "<text>"} — terminal, failure path.

Acceptance Criteria (EARS notation)
M3 backend acceptance criteria (AC-1 through AC-13) remain in force — all
streaming, failure-handling, and validation behavior is preserved. The
criteria below are additive; where they touch the upstream messages array,
they extend the M3 construction rule.
Backend (pytest-verified):

AC-1: WHEN a client POSTs with a valid message and a non-empty
history array, THE SYSTEM SHALL include the history entries in the
messages array sent to LLM_ENDPOINT, preserving their order.
AC-2: WHERE LLM_SYSTEM_PROMPT is non-empty AND history is
non-empty, THE SYSTEM SHALL construct the upstream messages as:
system-prompt message, then history entries in order, then the current
user message — in that exact sequence.
AC-3: WHERE LLM_SYSTEM_PROMPT is empty or unset AND history is
non-empty, THE SYSTEM SHALL construct the upstream messages as:
history entries in order, then the current user message — no system
message present.
AC-4: WHEN history is absent from the request body OR is an empty
array, THE SYSTEM SHALL construct the upstream messages identically to
M3 (system prompt if set, then current user message only).
AC-5: WHEN history contains an entry whose role is not "user"
or "assistant", THE SYSTEM SHALL respond HTTP 422 without opening an
SSE stream.
AC-6: WHEN history contains an entry missing the role or
content field, THE SYSTEM SHALL respond HTTP 422 without opening an
SSE stream.
AC-7: All M3 acceptance criteria governing SSE streaming (AC-1
through AC-12 of M3) and validation (M3 AC-13) remain in force,
unchanged by the addition of history.

Frontend (CEO-demo-verified):

AC-8: WHEN a turn completes successfully (done event received),
THE SYSTEM SHALL store the user's message (role "user") and the
accumulated assistant response (role "assistant") in the conversation
history, and include them in subsequent requests.
AC-9: WHEN a turn fails (error event received, whether or not
token events preceded it), THE SYSTEM SHALL NOT add the failed turn to
the conversation history sent on subsequent requests. Display behavior
is unchanged from M3 (the error/partial content remains visible).
AC-10: WHEN the page is refreshed or reloaded, THE SYSTEM SHALL
start with an empty conversation history.
AC-11: WHEN the user sends a follow-up message that references
information from a prior successful turn, THE MODEL'S response SHALL
demonstrate awareness of that prior context.

Out of Scope

Server-side conversation storage or persistence (database, file, session
store). History is client-managed and transient.
Browser-level persistence (localStorage, sessionStorage, IndexedDB). Page
refresh clears conversation.
Conversation management UI (new-chat button, multiple conversations,
clear-history button). Refresh is the clear mechanism.
Context-window management (truncation, summarization, sliding window).
If the accumulated history exceeds the LLM's context limit, the existing
error-handling path (fallback message) applies.
Editing, deleting, or regenerating individual messages.
Enforcing strict user/assistant alternation in the history array.
Validation ensures type correctness (role enum, content present); ordering
is the client's responsibility.
Any change to GET /, page markup/layout, SSE wire format, or failure
handling beyond what is specified above.

Flagged Assumptions (CEO sign-off before freeze)

A1 (load-bearing): History is client-managed. The server is stateless
— it receives, validates, and forwards history; it does not store it.
Page refresh or tab close loses the conversation. This is the simplest
design that delivers multi-turn; persistence is a clean future milestone.
A2: Only successful turns (done received) enter the history array.
Error turns are displayed but excluded from future LLM context — the
fallback message is system chrome, not model output.
A3: No maximum history length is enforced at the server or client.
If the conversation grows beyond the LLM's context window, the upstream
will error, and the existing error-handling path applies.
A4: The history field is optional with a default of []. A client
sending an M3-shaped request (no history key) gets M3-identical
behavior — backward compatible.
A5: The server does not enforce strict user/assistant alternation in
history. It validates types only. Non-alternating history is unlikely
in normal use (the frontend alternates naturally) and not harmful if
it occurs.

CEO Demo Script

Start LM Studio (or any OpenAI-compatible server) on :1234 with a
model loaded.
Run the app, open the page, send: "My name is Alice." — confirm a
normal streamed reply.
Send: "What is my name?" — confirm the model replies with awareness of
"Alice" (proving it received the prior turn as context).
Continue a few more turns referencing earlier content — confirm
coherent multi-turn behavior.
Refresh the page. Send: "What is my name?" — confirm the model does NOT
know (proving history was cleared on refresh).
Stop the model server mid-reply — confirm the partial text plus
fallback appears (M3 behavior preserved). Then send a new message after
restarting the server — confirm the failed turn is NOT in the
conversation context (the model doesn't reference the partial reply).
