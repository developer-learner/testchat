# ERD-DELTA v122 — chat failures show one generic retry line (no model-switch suggestion)

Freeze context: a CEO product decision (2026-09-03). testchat now delegates
model load/unload to Vortex, so the router-not-ready error's "pick a local
model" suggestion is obsolete. Every chat failure should surface a single calm
generic retry line with no suggestion. This is a focused behavioral delta on
one file (`src/api/chat.py`): it collapses the message-less-error path onto the
generic fallback message, superseding AC-179 with AC-182 (which matches the
already-generic still-ready case, AC-180).

## Design

- `src/api/chat.py`'s `event_generator` previously computed `routed_to_router`
  and a `_messageless_error()` helper returning a model-specific
  "not ready in Vortex — pick a local model" line for the 404 race and the
  generic `FALLBACK_REPLY` otherwise. The helper now always returns
  `llm_mod.FALLBACK_REPLY`; the `routed_to_router` computation and the Vortex
  readiness re-probe are removed.
- No other file changes. `stream_reply` still reports transport failure as a
  message-less `("error",)`; the stream loop still relays `item[1]` when a
  message is present. Only the message-less fallback text changes.

## Changed acceptance criteria

- **AC-182 (new):** the router-routed, message-less, model-left-the-ready-set
  error (the 404 race) now emits the generic fallback error message, identical
  to the still-ready case (AC-180) — one calm generic retry line, no
  model-switch suggestion. The response stays a 200 SSE stream.

## Superseded acceptance criteria

- **AC-179:** the model-specific `Model {id} is not ready in Vortex. Pick a
  local model or retry once it is loaded.` notice is retired. testchat
  delegates model load/unload to Vortex, so a local-model fallback offer is
  obsolete; AC-182 replaces it with the generic message.

## Changed files

- `src/api/chat.py`: `_messageless_error()` always returns
  `llm_mod.FALLBACK_REPLY`; the `routed_to_router` local and the Vortex
  readiness re-probe are removed. No other file changes.

## Coder briefs (verbatim)

### T1 — src/api/chat.py

Edit only `src/api/chat.py`. In `event_generator`, remove the `routed_to_router`
local and simplify `_messageless_error()` so it takes no router context and
always returns `llm_mod.FALLBACK_REPLY`. Do not change routing, imports,
token/think/done handling, the stream-loop `item[1]` relay, or any other file.
Acceptance: the 404-race and still-ready router errors both emit the generic
`FALLBACK_REPLY`; message-bearing errors are unchanged.

## Task DAG

Single task; no dependencies. `src/api/chat.py` is the only changed file.

## Test-to-file mapping

* `tests/test_router_route.py::test_chat_router_404_race_surfaces_not_ready_message` -> `src/api/chat.py`
* `tests/test_router_route.py::test_chat_router_error_while_still_ready_is_generic` -> `src/api/chat.py`
