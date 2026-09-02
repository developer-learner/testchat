# ERD-DELTA v116 — T3 brief clarification: the not-ready re-probe hooks the message-less `("error",)` item (chat.py only)

Freeze context: standing spec v115 (router recut onto Vortex's full ready
set). v115's T3 (`src/api/chat.py`) escalated caps-exhausted: the oracle is
correct, but the EM-composed brief placed the AC-179 not-ready re-probe in
the SSE generator's outer Python `except` handler. `src/services/llm.py`'s
`stream_reply()` converts a mid-stream transport failure (including the 404
when a router model has unloaded) into a **message-less `("error",)` item
yielded through the normal stream loop**, not a raised exception — so the
`except` handler never runs for the race the oracle exercises, and the item
receives the generic fallback. This delta re-scopes `src/api/chat.py` only,
restates the AC-178/179/180 chat behavior, and carries a TPM-authored
verbatim T3 brief that names the exact code location. No test, contract
oracle, AC, or `src/services/models.py` change: `models.py` (v115 T1) is
complete and moves to acceptance-only.

## Design

- The AC-179 discriminator lives in `src/api/chat.py`'s stream loop, in the
  existing `elif item[0] == "error":` branch — the branch that today turns a
  message-less `("error",)` item into `llm_mod.FALLBACK_REPLY`. It is NOT the
  outer `except (ConnectionError, TimeoutError, OSError)` handler:
  `stream_reply()` swallows transport failures into `("error",)` items
  (`src/services/llm.py` unchanged, per v115), so the `except` path is not
  the seam the 404 race travels.
- A request is router-routed iff `endpoint_override` was set to
  `models_mod.router_chat_endpoint()`. When a message-less `("error",)` item
  arrives on a router-routed request, re-probe with
  `models_mod.is_router_model(request.model)`; if it is now `False` (the
  model left the ready set) emit the exact not-ready message —
  `Model {id} is not ready in Vortex. Pick a local model or retry once it is
  loaded.` (AC-179). If it is still `True`, or the error item carried a
  message, or the request was not router-routed, keep the generic fallback
  (AC-180). The re-probe is the discriminator.
- The same decision covers a genuinely-raised message-less transport error
  in the outer `except` (defense-in-depth; the oracle drives the
  `("error",)`-item path, so a single shared local helper keeps both
  consistent).
- Transport seams unchanged; `src/services/models.py`, `src/services/llm.py`,
  and every other file are untouched.

## Changed acceptance criteria

- AC-178 (restated from v115): a router model not in the ready set is not
  rejected pre-stream — the request falls through to the local path.
- AC-179 (restated from v115): a router-routed stream error after the model
  left the ready set surfaces the exact not-ready message with a local
  fallback offer, as a 200 SSE error event — emitted from the message-less
  `("error",)` branch of the stream loop.
- AC-180 (restated from v115): a router-routed stream error while the model
  is still ready keeps the generic fallback message.

## Superseded acceptance criteria

- None. AC-178/179/180 stand as frozen in v115; this delta only clarifies the
  `src/api/chat.py` implementation location for AC-179/AC-180. No AC changes
  meaning; the oracle is byte-identical.

## Changed files

- `src/api/chat.py` (UPDATED): the message-less stream-error branch re-probes
  and emits the AC-179 not-ready message when the model has left the ready
  set, keeping the generic fallback otherwise (AC-180); the router routing
  branch and all other branches are unchanged from v115.
- `src/services/models.py` (no edit — acceptance-only): v115 T1 is complete
  and frozen; its `router_models()` / `is_router_model()` recut stands. Its
  mapped tests remain as acceptance-only observation.
- `src/api/models.py` (no edit — acceptance-only): unchanged, as in v115.

## Coder briefs (verbatim)

### T3 — src/api/chat.py (router 404 race: not-ready notice on the message-less error item)

Context you must honor: `src/services/llm.py` is NOT changed. Its
`stream_reply()` turns a transport failure — including the mid-stream 404
when a router model has unloaded — into a message-less `("error",)` tuple
that it YIELDS through the normal stream loop; it does not raise. So the
not-ready decision belongs in the stream loop's `elif item[0] == "error":`
branch, NOT the outer `except` handler. Do not implement AC-179 solely in
the outer exception handler; the oracle's race never raises.

Edit exactly `src/api/chat.py`, inside the `chat` endpoint's
`event_generator`. Make these changes and nothing else:

1. Compute one local boolean once, where `endpoint_override` is known to the
   generator: `routed_to_router = endpoint_override is not None and
   endpoint_override == models_mod.router_chat_endpoint()`. Add no new
   parameters and no module-level state.

2. In the stream loop's `elif item[0] == "error":` branch, decide the SSE
   error `message` as follows:
   - If the item is message-less (`len(item) == 1`) AND `routed_to_router`
     AND `models_mod.is_router_model(request.model)` is `False`: the message
     is exactly
     `Model {request.model} is not ready in Vortex. Pick a local model or
     retry once it is loaded.` (an f-string on `request.model`).
   - Otherwise: keep the current behavior — `item[1]` when
     `len(item) > 1`, else `llm_mod.FALLBACK_REPLY`.
   Emit it exactly as today: `event: error` with
   `data: {"message": <json.dumps(message)>}`.

3. Apply the SAME decision to a genuinely-raised message-less transport error
   in the outer `except (ConnectionError, TimeoutError, OSError) as e:`
   handler: when `not str(e)` AND `routed_to_router` AND
   `is_router_model(request.model)` is `False`, emit the same not-ready
   message; otherwise keep the existing fallback (`str(e)` when present, else
   `FALLBACK_REPLY`). Factor the shared decision into one small local helper
   so the `("error",)`-item path and the exception path cannot diverge.

Do not change `src/services/llm.py`, `src/services/models.py`, the router
routing branch, the `token`/`think`/`done` branches, imports, or any other
file. After editing, self-verify by reading the final file: a message-less
`("error",)` on a router-routed request whose model has left the ready set
yields the exact not-ready string; a still-ready model, a message-bearing
error, and a non-router request all keep the generic fallback; and the raised
message-less exception path makes the identical decision.

## Test-to-file mapping

* `tests/test_router_route.py::test_chat_routes_router_model_to_router_endpoint_and_passes_model`
  -> `src/api/chat.py`
* `tests/test_router_route.py::test_chat_internal_path_untouched_when_vortex_url_unset`
  -> `src/api/chat.py`
* `tests/test_router_route.py::test_chat_router_model_not_listed_falls_through_to_local_path`
  -> `src/api/chat.py`
* `tests/test_router_route.py::test_chat_router_model_router_down_falls_through_to_local_path`
  -> `src/api/chat.py`
* `tests/test_router_route.py::test_chat_router_404_race_surfaces_not_ready_message`
  -> `src/api/chat.py`
* `tests/test_router_route.py::test_chat_router_error_while_still_ready_is_generic`
  -> `src/api/chat.py`
