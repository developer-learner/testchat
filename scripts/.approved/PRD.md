PRD — testchat M5: Model Selection & Nemotron Runtime

Milestone
M5. Two additions on top of M4's conversation history: (1) let the user see and select from whatever models are currently loaded in LM Studio, and (2) let the app itself load and unload a separate local model, Nemotron, which runs outside LM Studio via its own standalone server process. LM Studio's own models are detected only — the app never loads or unloads them; that remains a manual action in the LM Studio UI. Model choice is a session-level decision: once the user sends the first message of a conversation, the model selector locks for that conversation. Page refresh (which already clears history per M4) also unlocks selection.

What

GET /api/v1/models — returns the models currently usable for chat: every model LM Studio reports as loaded (proxied from LM Studio's own `GET /v1/models`), plus an entry for `nemotron` if and only if Nemotron is currently loaded via this app. If LM Studio is unreachable, its portion of the list degrades to empty rather than failing the whole endpoint (consistent with M3/M4's failure-containment posture).
POST /api/v1/nemotron/load — spawns the Nemotron runtime as a subprocess, waits for it to report ready (up to 30 seconds), and returns success once confirmed. If Nemotron is already loaded, this is a no-op success (idempotent). If readiness isn't reached within 30 seconds, the subprocess is terminated and the endpoint reports failure.
POST /api/v1/nemotron/unload — terminates the Nemotron subprocess if running. If it isn't running, this is a no-op success (idempotent).
POST /api/v1/chat gains an optional model field. `"model": "nemotron"` routes the request to the Nemotron runtime instead of LM Studio. Any other value, or an absent/null field, routes to LM Studio exactly as in M3/M4 — unchanged behavior for existing clients. If `"model": "nemotron"` is sent while Nemotron is not currently loaded, the request is rejected (422) before any stream opens.
Frontend (src/static/index.html): a model selector populated from GET /api/v1/models, plus Load Nemotron / Unload Nemotron controls. The selector is enabled only before the first message of a conversation is sent; once a message is sent, it locks until the next page refresh. All SSE mechanics, failure containment, and conversation-history behavior from M3/M4 are unchanged regardless of which backend a chat request is routed to.

Fixed constants (new)

Nemotron runtime is reached at a fixed local base URL, not an environment variable — this is app-internal wiring for a specific companion process, not a deployment-configurable endpoint like LLM_ENDPOINT.
Nemotron readiness timeout: 30 seconds. Termination grace period before a hard kill: 5 seconds.

Acceptance Criteria (EARS notation)
All M3 and M4 acceptance criteria remain in force, unchanged. The criteria below are additive.

Backend (pytest-verified):

AC-1: WHEN a client GETs /api/v1/models AND LM Studio's models endpoint responds successfully, THE SYSTEM SHALL return every model LM Studio reports, each tagged with source "lmstudio".
AC-2: WHEN LM Studio's models endpoint is unreachable or errors, THE SYSTEM SHALL respond 200 with an empty list for the LM Studio portion, rather than failing the request.
AC-3: WHEN Nemotron is not currently loaded via this app, THE SYSTEM SHALL omit it entirely from the /api/v1/models response.
AC-4: WHEN a client POSTs /api/v1/nemotron/load AND Nemotron is not already loaded, THE SYSTEM SHALL spawn the Nemotron runtime and respond with status "loaded" once readiness is confirmed within 30 seconds.
AC-5: WHEN a client POSTs /api/v1/nemotron/load AND Nemotron is already loaded, THE SYSTEM SHALL respond with status "loaded" without spawning a second instance.
AC-6: WHEN Nemotron does not become ready within 30 seconds of being spawned, THE SYSTEM SHALL terminate the spawned process and respond HTTP 503 with status "error".
AC-7: WHEN a client POSTs /api/v1/nemotron/unload AND Nemotron is loaded, THE SYSTEM SHALL terminate the process and respond with status "unloaded".
AC-8: WHEN a client POSTs /api/v1/nemotron/unload AND Nemotron is not loaded, THE SYSTEM SHALL respond with status "unloaded" without error.
AC-9: WHEN a chat request's model field equals "nemotron" AND Nemotron is loaded, THE SYSTEM SHALL direct the upstream request to the Nemotron runtime instead of LLM_ENDPOINT.
AC-10: WHEN a chat request's model field is absent, null, or any value other than "nemotron", THE SYSTEM SHALL direct the upstream request to LLM_ENDPOINT exactly as in M3/M4.
AC-11: WHEN a chat request's model field is present and is not a string, THE SYSTEM SHALL respond HTTP 422 without opening an SSE stream.
AC-12: WHEN a chat request specifies model "nemotron" AND Nemotron is not currently loaded, THE SYSTEM SHALL respond HTTP 422 without opening an SSE stream.

Frontend (CEO-demo-verified):

AC-13: WHEN the page loads, THE SYSTEM SHALL populate the model selector from GET /api/v1/models.
AC-14: WHEN the user sends the first message of a conversation, THE SYSTEM SHALL lock the model selector for the remainder of that conversation.
AC-15: WHEN the page is refreshed, THE SYSTEM SHALL unlock the model selector and refresh its contents.
AC-16: WHEN the user clicks Load Nemotron and the call succeeds, THE SYSTEM SHALL add "nemotron" as a selectable option.
AC-17: WHEN the user clicks Unload Nemotron and the call succeeds, THE SYSTEM SHALL remove "nemotron" from the selectable options.

Out of Scope

Loading, unloading, or switching LM Studio's own models from the app. Detection only; the user manages LM Studio manually.
Any model besides Nemotron being loadable/unloadable by the app.
Switching models mid-conversation.
Persisting model choice across refresh.
Any check or handling of memory coexistence between Nemotron and whatever LM Studio has loaded.
Authentication/authorization on the new routes.
Any change to GET /, SSE wire format, or M3/M4 failure-handling behavior beyond routing target selection.

Flagged Assumptions (CEO sign-off before freeze)

A1: LM Studio's OpenAI-compatible GET /v1/models (same host:port as LLM_ENDPOINT, path derived by stripping the /chat/completions suffix) is the source of truth for "currently loaded" models. Verified against LM Studio's published API documentation.
A2: The Nemotron runtime is launched as `python3 ~/nemotron-vmlx.py`, exposing an OpenAI-compatible server on `http://localhost:8000`, with readiness determined by that server responding to GET /v1/models.
A3: No new environment variables are introduced. The LM Studio base URL is derived internally from the existing LLM_ENDPOINT; the Nemotron base URL is a fixed internal constant, since only one such companion process is in scope.
A4: Unload is a process termination (SIGTERM, escalating to SIGKILL after 5s) — the Nemotron runtime exposes no graceful shutdown API of its own.
A5: Redundant load/unload calls (already in the target state) are treated as success, not error.
A6: Nemotron readiness and chat-completions paths both live under Nemotron's own /v1/* — the same assumption LM Studio itself uses.

CEO Demo Script

With LM Studio running and at least one model loaded, open the page — confirm the model selector lists it.
Click Load Nemotron — after a short wait, confirm "nemotron" appears as a selectable option.
Select Nemotron, send a message — confirm a normal streamed reply, and confirm the model selector is now locked.
Refresh the page — confirm the selector is unlocked again and repopulated.
Click Unload Nemotron — confirm it disappears from the list.
Attempt to select "nemotron" via a raw request without loading it first (or after unloading) — confirm the request is rejected rather than silently falling back.
