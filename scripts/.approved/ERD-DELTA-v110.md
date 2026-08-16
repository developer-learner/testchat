# ERD-DELTA v110 — router model: convergent task DAG (v109 follow-on)

Freeze context: standing spec v109. v107 introduced the router feature
(AC-170..AC-174); v108 repaired smoke-check coverage for `src/static/threads.js`;
v109 registered the milestone's twenty test-to-file pins in the frozen
`contracts.test_mapping` data plane. v110 fixes the remaining plan-gate
defect: the task DAG did not converge (T4, T5, T6, T7, T8 were five sinks),
so D-64 could not auto-place browser test files and the plan gate rejected
the milestone. This freeze chains the DAG into a single topological order
(T1 -> T2 -> T3 -> T4 -> T5 -> T6 -> T7 -> T8) with exactly one final task
(T8), where every task's dependency closure is the full inventory. No
behavior changes: AC-170..AC-174 stand exactly as frozen in v107, no
application file changes, no test bytes change.

## Changed acceptance criteria

None. AC-170..AC-174 were introduced by v107 and remain in force unchanged;
this freeze alters acceptance *wiring* only (task-DAG convergence), never a
criterion.

## Superseded acceptance criteria

None.

## Changed files

- `src/services/models.py` (edited, v107) — router service seams: constant
  `ROUTER_MODEL_ID` (env `ROUTER_MODEL_ID`, default `qwen3.8-27b-8bit`),
  `is_router_configured()`, `router_models()`, `is_router_model()`,
  `router_chat_endpoint()`, and the router entry appended to the result of the
  existing `list_models()` between the LM Studio block and the `SCRIPT_MODELS`
  loop.
- `src/api/models.py` (edited, v107) — the `ModelInfo` `source` `Literal`
  gains the value `router`; nothing else changes.
- `src/api/chat.py` (edited, v107) — inside the existing `if request.model:`
  block, after the script-model branch, a router branch gated on
  `models_mod.is_router_configured()`: not-listed -> the same 422 contract as
  a not-loaded script model; listed -> `endpoint_override =
  router_chat_endpoint()`. With `VORTEX_URL` unset every path stays
  byte-identical.
- `src/static/catalog.js` (no_edit, declared for test-ownership only) — the
  existing dropdown merge renders a router-sourced list entry without any
  change to this file.
- `src/services/storage.py`, `src/api/threads.py`, `src/static/threads.js`,
  `src/static/app.js` (no_edit, carried-owner declarations) — standing
  behavior is pinned via `contracts.test_mapping` and `contracts.smoke_checks`;
  no code change.
- `scripts/.approved/contracts.json` (repair, registered at v109) — the
  milestone's twenty test-to-file pins live in `contracts.test_mapping`;
  `smoke_checks` retains the standing three entries plus the v108
  `threads.js` entry. v110 changes the ERD-DELTA task DAG only.

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
* `tests/test_ui_catalog.py::test_model_dropdown_lists_router_model_from_models_list[chromium]`
  -> `src/static/catalog.js`
* `tests/test_storage_service.py::test_roundtrip_preserves_snapshot`
  -> `src/services/storage.py`
* `tests/test_data_safety_storage.py::test_valid_json_with_invalid_thread_schema_is_quarantined`
  -> `src/api/threads.py`
* `tests/test_data_safety_ui.py::test_delete_one_thread_survives_reload[chromium]`
  -> `src/static/threads.js`
* `tests/test_data_safety_ui.py::test_hydration_failure_warns_retries_and_recovers_saving[chromium]`
  -> `src/static/app.js`

Every pin above is registered in the frozen `contracts.test_mapping` data
plane (v109); the ERD-DELTA section remains as the freeze-time pin-gate and
B3 synthesis source.

## Task DAG

`src/static/app.js` depends on `src/static/threads.js`
`src/static/threads.js` depends on `src/api/threads.py`
`src/api/threads.py` depends on `src/services/storage.py`
`src/services/storage.py` depends on `src/static/catalog.js`
`src/static/catalog.js` depends on `src/api/models.py`
`src/static/catalog.js` depends on `src/api/chat.py`
`src/api/models.py` depends on `src/services/models.py`
`src/api/chat.py` depends on `src/services/models.py`
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
script-model branch; both router outcomes are present (listed -> override,
not listed -> 422 before any streaming); with `VORTEX_URL` unset the
function body is byte-identical to the pre-edit file.

### T4 — src/static/catalog.js (router dropdown presence)

No code change. The existing `fetchModels` flow merges the models list and
the catalog by id and renders one option per id; a list entry with id
`qwen3.8-27b-8bit` and source `router` therefore renders as a selectable
(script:false, loaded:true) option without any edit to this file. This task
owns the mapped browser test
(`test_model_dropdown_lists_router_model_from_models_list`) which simulates
the API payloads via page.route and asserts the option renders exactly once.
Self-verify: run the mapped test; it must pass without any working-tree
change to this file.

### T5 — src/services/storage.py (carried-owner acceptance)

No code change. This file is in the inventory so the standing storage
behavior stays pinned (the mapped regression test
`test_roundtrip_preserves_snapshot` pins it as behavioral owner); the delta
touches none of its behavior. This task exists so the carried pin stays
in-inventory; it owns no acceptance signal beyond the carried regression
test, which the milestone's full mapped scope runs. Self-verify: confirm no
working-tree change to this file; run the pinned test, which must pass
untouched.

### T6 — src/api/threads.py (carried-owner acceptance)

No code change. In the inventory because `contracts.test_mapping` pins
`tests/test_data_safety_storage.py::test_valid_json_with_invalid_thread_schema_is_quarantined`
to it as behavioral owner. No delta behavior touches this file; the task
exists so the carried pin stays in-inventory. Self-verify: confirm no
working-tree change to this file; the pinned regression test passes
untouched.

### T7 — src/static/threads.js (carried-owner acceptance)

No code change. In the inventory because `contracts.test_mapping` pins
`tests/test_data_safety_ui.py::test_delete_one_thread_survives_reload` to it
as behavioral owner, and `contracts.smoke_checks` carries the entry
`grep -q '_enqueueMutation' src/static/threads.js`. No delta behavior touches
this file; the task exists so the carried pin and smoke check stay
in-inventory. Self-verify: confirm no working-tree change to this file; the
pinned regression test passes untouched.

### T8 — src/static/app.js (carried-owner acceptance)

No code change. In the inventory because `contracts.test_mapping` pins
`tests/test_data_safety_ui.py::test_hydration_failure_warns_retries_and_recovers_saving`
to it as behavioral owner. No delta behavior touches this file; the task
exists so the carried pin stays in-inventory. Self-verify: confirm no
working-tree change to this file; the pinned regression test passes
untouched.

## Flagged assumptions (delta-level)

- The converged chain makes T8 the single final task: the D-64 browser-test
  auto-placement can resolve every node-id, while the pinned catalog test
  stays at T4 (its registered owner; pinned node-ids are exempt from
  movement). T1..T8 all share the full-inventory dependency closure, so no
  acceptance node-id ever lands on a task whose closure lacks it.
- The chain serializes the acceptance-only tasks T5..T8; their cost is
  negligible (no code change, mapped tests only) and the determinism gain
  outweighs the lost parallelism.
- Registration (v109) holds: every key exists as a frozen node-id in
  `scripts/.approved/test-nodeids`, and D-124 auto-placement now owns
  placement of all twenty node-ids.
- `smoke_checks` entries for `src/static/threads.js` are green-on-unchanged
  by contract (the file is in `no_edit_files`), so the M35 red-check skips
  them; their purpose is the plan gate's per-task acceptance signal, not a
  behavioral probe.
- AC-170..AC-174 remain exactly as frozen in v107; v108..v110 are
  bookkeeping repairs that must not re-price the milestone.