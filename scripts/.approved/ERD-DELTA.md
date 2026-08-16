# ERD-DELTA v107 — router model (dual-path via the vortex universal surface)

Freeze context: standing spec v106. This delta is additive: testchat gains a
redundant chat route through the vortex universal endpoint
(`{VORTEX_URL}/v1/chat/completions`, `VORTEX_URL` default
`http://localhost:9000`) while every existing internal wiring (LM Studio
`LLM_ENDPOINT` path, script-model lifecycle, nemotron routing) stays byte
identical. The router model `qwen3.8-27b-8bit` is presented like an LM Studio
model — a list entry, never a catalog entry — so the existing dropdown merge
(`mergeModel` in `src/static/catalog.js`) renders it with zero UI changes and
the script-model load/unload machinery is structurally never involved.

## Changed acceptance criteria

* **AC-170:** WHEN `VORTEX_URL` is set AND the router at
  `{VORTEX_URL}/v1/models` answers HTTP 200 with `qwen3.8-27b-8bit` listed in
  its `data`, THE SYSTEM SHALL include the model `qwen3.8-27b-8bit` with
  source `router` in the response of `GET /api/v1/models`, such that the
  router model appears in the model dropdown as a selectable chat model.

* **AC-171:** WHEN the router probe fails (non-200 status or connection
  error) or the router does not list `qwen3.8-27b-8bit`, THE SYSTEM SHALL
  omit the router model from `GET /api/v1/models` and SHALL never include it
  in `GET /api/v1/models/catalog`, such that the dropdown never offers a chat
  that cannot succeed and the script-model load/unload machinery never
  becomes involved with the router model.

* **AC-172:** WHEN a chat request names `qwen3.8-27b-8bit` AND the router
  lists it, THE SYSTEM SHALL stream the reply from
  `{VORTEX_URL}/v1/chat/completions` with the model id passed through
  unchanged, such that the router — not the internal endpoints — answers.

* **AC-173:** WHEN a chat request names the router model id and the router
  does not list it at that moment, THE SYSTEM SHALL reject the request with
  422 before any streaming begins — the same contract as a not-loaded script
  model — such that the request never silently falls through to a different
  backend.

* **AC-174:** WHEN `VORTEX_URL` is not set, THE SYSTEM SHALL expose no router
  model and perform no router probe, such that existing deployments behave
  exactly as before.

## Superseded acceptance criteria

None. This delta is purely additive; no criterion is retired, amended, or
superseded.

## Changed files

- `src/services/models.py` (edited) — router service seams: new module
  constant `ROUTER_MODEL_ID` (env `ROUTER_MODEL_ID`, default
  `qwen3.8-27b-8bit`), new functions `is_router_configured()`,
  `router_models()`, `is_router_model()`, `router_chat_endpoint()`, and a
  router entry appended to the result of the existing `list_models()` (the LM
  Studio block and the `SCRIPT_MODELS` loop stay byte identical;
  `router_models()` is called between them).
- `src/api/models.py` (edited) — the `ModelInfo` `source` `Literal` gains the
  value `router`; no other response model changes.
- `src/api/chat.py` (edited) — inside the existing `if request.model:` block,
  after the script-model branch, a router branch: when
  `models_mod.is_router_configured()` is true AND `request.model` equals
  `ROUTER_MODEL_ID`, gate on `is_router_model()`; on failure raise the
  same 422 contract as a not-loaded script model; on success set
  `endpoint_override` to `router_chat_endpoint()`. Every other path
  (including `endpoint_override = None` default) stays byte identical, so
  with `VORTEX_URL` unset any model id takes the pre-existing generic path.
- `src/static/catalog.js` (no_edit, declared for test-ownership only) — the
  dropdown already merges the models list (`lmModels[i].id` → option,
  `script:false`); a router-sourced list entry renders without any change to
  this file. Declared in the inventory so the new UI oracle pins its owner
  file. The orchestrator must never invoke the coder for it.
- `src/services/storage.py`, `src/api/threads.py`, `src/static/threads.js`,
  `src/static/app.js` (no_edit, carried-owner declarations only) — standing
  `contracts.test_mapping` pins their behavior; the carried pins must stay
  in-inventory. No code change; acceptance-only tasks.

## Test-to-file mapping

* `tests/test_router_route.py::test_router_models_lists_router_when_router_reports_it`
  -> `src/services/models.py`
* `tests/test_router_route.py::test_router_models_empty_when_router_omits_it`
  -> `src/services/models.py`
* `tests/test_router_route.py::test_router_models_empty_when_router_503`
  -> `src/services/models.py`
* `tests/test_router_route.py::test_router_models_empty_when_probe_raises`
  -> `src/services/models.py`
* `tests/test_router_route.py::test_router_models_empty_when_vortex_url_unset`
  -> `src/services/models.py`
* `tests/test_router_route.py::test_is_router_configured_reflects_env`
  -> `src/services/models.py`
* `tests/test_router_route.py::test_router_models_deduplicated`
  -> `src/services/models.py`
* `tests/test_router_route.py::test_router_chat_endpoint_uses_vortex_url`
  -> `src/services/models.py`
* `tests/test_router_route.py::test_router_models_included_in_list_models`
  -> `src/services/models.py`
* `tests/test_router_route.py::test_router_model_never_in_catalog`
  -> `src/api/models.py`
* `tests/test_router_route.py::test_get_models_includes_router_when_ready`
  -> `src/api/models.py`
* `tests/test_router_route.py::test_chat_routes_router_model_to_router_endpoint_and_passes_model`
  -> `src/api/chat.py`
* `tests/test_router_route.py::test_chat_router_model_not_listed_is_422`
  -> `src/api/chat.py`
* `tests/test_router_route.py::test_chat_router_model_router_down_is_422`
  -> `src/api/chat.py`
* `tests/test_router_route.py::test_chat_internal_path_untouched_when_vortex_url_unset`
  -> `src/api/chat.py`
* `tests/test_ui_catalog.py::test_model_dropdown_lists_router_model_from_models_list`
  -> `src/static/catalog.js`

(UPDATED) `tests/test_ui_catalog.py` is a carried file restaged with the one
added browser test pinned above.

## Task DAG

`src/api/models.py` depends on `src/services/models.py`
`src/api/chat.py` depends on `src/services/models.py`
`src/static/catalog.js` depends on `src/services/models.py`
Task order: T1 (router service seams) -> T2 (router source in the models API) -> T3 (router chat branch) -> T4 (router dropdown presence) -> T5 (carried-owner acceptance) -> T6 (carried-owner acceptance) -> T7 (carried-owner acceptance) -> T8 (carried-owner acceptance)

## Coder briefs (verbatim)

### T1 — src/services/models.py (router service seams)

Add a router (vortex universal surface) section to this file, following the
existing conventions in the module.

1. Add one module-level constant with the other env-derived constants:
   `ROUTER_MODEL_ID = os.environ.get("ROUTER_MODEL_ID", "qwen3.8-27b-8bit")`.
   The router base URL is read at call time from the environment inside the
   new functions (never a module-level constant), mirroring how the existing
   `list_models` reads `LLM_ENDPOINT` at call time: a helper returning
   `os.environ.get("VORTEX_URL") or None`.
2. Add `def is_router_configured() -> bool:` returning `True` iff the
   call-time `VORTEX_URL` value is a non-empty string, `False` otherwise.
   This is the single gate deciding whether the router path exists at all.
3. Add `def router_chat_endpoint() -> str:` returning
   `base + "/v1/chat/completions"` for the call-time base from the helper.
4. Add `def router_models() -> list[dict]:` — when `VORTEX_URL` is unset,
   return `[]` WITHOUT issuing any probe (the configuration gate runs before
   the HTTP call). Otherwise probe `GET {base}/v1/models` with
   `httpx.get(base + "/v1/models", timeout=2)`. Any exception or a non-200
   status returns `[]`. On 200, parse the
   JSON `data` array (entries are objects with string `id` fields, e.g. the
   vortex universal surface's `{"object": "list", "data": [{"id": ...}]}`
   shape). Return the list `[{"id": ROUTER_MODEL_ID, "source": "router"}]`
   exactly once when some `data` entry's `id` equals `ROUTER_MODEL_ID`,
   otherwise `[]`. Share the probe logic with `is_router_model` so both
   observe the same response.
5. Add `def is_router_model(model_id: str) -> bool:` returning `True` iff
   `model_id == ROUTER_MODEL_ID` and the shared probe lists it; `False` on
   any probe failure and when `VORTEX_URL` is unset.
6. Extend the existing `list_models()`: after the LM Studio block and before
   the `SCRIPT_MODELS` loop, extend the returned list with
   `router_models()`. Each router dict carries `id` and `source` keys only.

Do not change the signature, order, or behavior of any existing function or
constant in this file. After editing, self-verify by reading the final file:
all four new functions exist with the exact names and return shapes given,
`ROUTER_MODEL_ID` defaults to `qwen3.8-27b-8bit`, and `list_models` calls
`router_models` in the position described.

### T2 — src/api/models.py (router source in the models API)

Edit exactly one thing in this file: extend the `ModelInfo` class's `source`
`Literal` — currently
`"lmstudio", "nemotron", "deepseek-v4-flash-0731", "Flash_Q2KXL", "Flash_IQ3XXS"`
— with the additional value `"router"`. Nothing else in this file changes:
no new routes, no other schema edits, the load/unload endpoints stay byte
identical. After editing, self-verify by reading the final file: the
`Literal` contains `"router"`, and `CatalogEntry`'s `source` `Literal` is
untouched.

### T3 — src/api/chat.py (router chat branch)

Inside the existing `if request.model:` block in the `chat` endpoint, after
the script-model branch and before the function's `endpoint_override = None`
fall-through (the `endpoint_override` variable keeps its current default
initialization):

1. Add a router branch: when `models_mod.is_router_configured()` is true AND
   `request.model == models_mod.ROUTER_MODEL_ID` and the script-model branch
   did not handle it, call `models_mod.is_router_model(request.model)`; when
   it returns `False`, raise
   `HTTPException(status_code=422, detail=f"Model {request.model} is not loaded")`
   — the exact 422 contract the script-model branch uses; when it returns
   `True`, set `endpoint_override = models_mod.router_chat_endpoint()`.
   When `is_router_configured()` is false, no model id enters this branch —
   every id takes the pre-existing generic path byte-identically.
2. Make the router functions reachable by adding a module import:
   `import src.services.models as models_mod` (the existing
   `from src.services.models import get_script_model, is_script_model_loaded`
   import stays as is).

Every other path in this file stays byte identical: the generic
`endpoint_override = None` default, the script-model branch, the SSE event
generator, and the exception collapse. After editing, self-verify by reading
the final file: the router branch sits inside `if request.model:` after the
script-model branch; both router outcomes are present (listed → override,
not listed → 422 before any streaming); with `VORTEX_URL` unset the
function body is byte-identical to the pre-edit file.

### T4 — src/static/catalog.js (router dropdown presence)

No code change. The existing `fetchModels` flow merges the models list and
the catalog by id and renders one option per id; a list entry with id
`qwen3.8-27b-8bit` and source `router` therefore renders as a selectable
(script:false, loaded:true) option without any edit to this file. This task
owns only the acceptance signal: the mapped browser test
(`test_model_dropdown_lists_router_model_from_models_list`) which simulates
the API payloads via page.route and asserts the option renders exactly once.
Self-verify: run the mapped test; it must pass without any working-tree
change to this file.

### T5 — src/services/storage.py (carried-owner acceptance)

No code change. This file is in the inventory solely because the standing
`contracts.test_mapping` pins
`tests/test_data_safety_storage.py::test_valid_json_with_invalid_thread_schema_is_quarantined`
to it as behavioral owner; the delta touches none of its behavior. This task
exists so the carried pin stays in-inventory; it owns no acceptance signal
beyond the carried regression test, which the milestone's full mapped scope
runs. Self-verify: confirm no working-tree change to this file; run the
pinned test, which must pass untouched.

### T6 — src/api/threads.py (carried-owner acceptance)

No code change. In the inventory because the standing `contracts.test_mapping`
pins `tests/test_data_safety_storage.py::test_valid_json_with_invalid_thread_schema_is_quarantined`
to it as behavioral owner. No delta behavior touches this file; the task
exists so the carried pin stays in-inventory. Self-verify: confirm no
working-tree change to this file; the pinned regression test passes
untouched.

### T7 — src/static/threads.js (carried-owner acceptance)

No code change. In the inventory because two standing `contracts.test_mapping`
pins name it as behavioral owner (the data-safety UI tests). No delta
behavior touches this file; the task exists so the carried pins stay
in-inventory. Self-verify: confirm no working-tree change to this file; the
pinned regression tests pass untouched.

### T8 — src/static/app.js (carried-owner acceptance)

No code change. In the inventory because the standing `contracts.test_mapping`
pins `tests/test_data_safety_ui.py::test_hydration_failure_warns_retries_and_recovers_saving[chromium]`
to it as behavioral owner. No delta behavior touches this file; the task
exists so the carried pin stays in-inventory. Self-verify: confirm no
working-tree change to this file; the pinned regression test passes
untouched.

## Flagged assumptions (delta-level)

- The vortex universal surface answers `GET /v1/models` with
  `{"object": "list", "data": [{"id": <public_id>, "object": "model"}]}`
  and forwards `POST /v1/chat/completions` bodies unchanged; the testchat
  probe treats any 200 as ready.
- The chat gate probes the router per request (same class as the existing
  script-model readiness checks); the probe is skipped entirely when
  `VORTEX_URL` is unset.
- `VORTEX_URL` is exported in the app process environment (e.g.
  `VORTEX_URL=http://localhost:9000` alongside the existing `LLM_ENDPOINT`
  exports); the pipeline and tests never rely on the app's runtime env.
