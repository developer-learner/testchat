# ERD-DELTA v112 — router model: probe timeout raised (T3 root cause fixed)

Freeze context: standing spec v111. The v111 re-run reproduced the v110 T3
gate failure (`422 == 200` on
`test_chat_routes_router_model_to_router_endpoint_and_passes_model`), so the
v111 "transient" classification was WRONG and is withdrawn. Root cause,
established mechanically: the router probe uses a 2-second timeout
(`httpx.get(base + "/v1/models", timeout=2)`, authored in the v107 brief).
An in-process experiment (sleep 3.2s before the probe's answer) flips the
same outcome: the probe returns not-listed -> the chat endpoint raises the
422 contract -> exactly the gate's evidence. The failing test is the ONLY
one of the four whose outcome depends on a live probe connect succeeding;
the other three pass precisely because they expect 422/None. Under a cold
sandbox container start (the gate's verdict run follows image build/extract
and the pytest process starts with heavily loaded scheduling), the
in-process pytest-httpserver thread can take longer than 2 seconds to serve
the probe, making the failure probe-timing-determined — a real spec
fragility, fixed here by raising the probe timeout.

This freeze changes ONE artifact: the T1 brief, which the coder re-executes
(`timeout=2` -> `timeout=5` in `_router_probe`). No AC changes
(AC-170..AC-174 stand as frozen in v107), no application file changes in
this freeze itself, no test bytes change; contracts registration intact.

## Changed acceptance criteria

None. AC-170..AC-174 were introduced by v107 and remain in force unchanged.

## Superseded acceptance criteria

None.

## Changed files

- `src/services/models.py`, `src/api/models.py`, `src/api/chat.py`
  (edited, v107) — the router feature as frozen in v107..v111; v112 re-runs
  T1 with the revised brief (probe timeout 2s -> 5s). The 422 evidence was
  NOT a chat.py defect; T3's implementation stands accepted.
- `src/static/catalog.js`, `src/services/storage.py`, `src/api/threads.py`,
  `src/static/threads.js`, `src/static/app.js` (no_edit, carried-owner
  declarations) — unchanged.
- `scripts/.approved/contracts.json` (v109/v110 registration) — unchanged by
  this freeze; the staged overlay restates the identical content at erd
  version 112 so the merge is a byte-identical no-op.

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

The v107..v111 brief is implemented and accepted; ONE revision now: in
`router_models()` / `is_router_model()`'s shared probe, raise the probe
timeout from 2 seconds to 5 seconds:

- `httpx.get(base + "/v1/models", timeout=2)` -> `timeout=5`.

Reason (spec defect, frozen at v112): under a cold sandbox container start,
the in-process test server can take longer than 2 seconds to serve the
first probe; the 2s timeout then flips the live-path outcome to
not-listed -> the chat endpoint's 422 — the T3 gate evidence. 5 seconds
covers cold-start scheduling while remaining a bounded probe.

Everything else in the v107 brief stands verbatim and is already accepted:
`ROUTER_MODEL_ID` constant, `is_router_configured()`, `router_chat_endpoint()`,
`router_models()`, `is_router_model()`, the `list_models()` append position,
and no change to any existing function. Self-verify by reading the final
file: the probe timeout literal is `5`, and all other accepted behavior is
unchanged.

### T2 — src/api/models.py (router source in the models API)

Already implemented and accepted (commit 83c15c4): the brief is unchanged.
No further work; the mapped tests are green.

### T3 — src/api/chat.py (router chat branch)

Already implemented and accepted (commit fb16089). The v110/v111 gate's 422
evidence is now conclusively attributed to the T1 probe timeout (fixed at
v112), not to this file. The brief is unchanged; no further work.

### T4 — src/static/catalog.js (router dropdown presence)

No code change. The existing `fetchModels` flow merges the models list and
the catalog by id; a list entry with id `qwen3.8-27b-8bit` and source
`router` renders as a selectable (script:false, loaded:true) option without
any edit. Acceptance: the mapped browser test passes with no working-tree
change to this file.

### T5 — src/services/storage.py (carried-owner acceptance)

No code change. The mapped regression test
`test_roundtrip_preserves_snapshot` pins this file as behavioral owner.
Self-verify: no working-tree change; the pinned test passes untouched.

### T6 — src/api/threads.py (carried-owner acceptance)

No code change. `contracts.test_mapping` pins
`test_valid_json_with_invalid_thread_schema_is_quarantined` to this file as
behavioral owner. Self-verify: no working-tree change; the pinned test
passes untouched.

### T7 — src/static/threads.js (carried-owner acceptance)

No code change. `contracts.test_mapping` pins
`test_delete_one_thread_survives_reload` to it as behavioral owner, and
`contracts.smoke_checks` carries
`grep -q '_enqueueMutation' src/static/threads.js`. Self-verify: no
working-tree change; the pinned test passes untouched.

### T8 — src/static/app.js (carried-owner acceptance)

No code change. `contracts.test_mapping` pins
`test_hydration_failure_warns_retries_and_recovers_saving` to it as
behavioral owner. Self-verify: no working-tree change; the pinned test
passes untouched.

## Flagged assumptions (delta-level)

- The v111 transient classification is withdrawn: the reproduction is
  explained by probe-timeout fragility, mechanism-verified (a >2s probe
  answer flips the outcome to 422 with timeout=2; 5s restores it).
- The fix is deliberately minimal (one integer literal in the probe) and
  cannot change any accepted behavior: 2s->5s only widens the bound.
- AC-170..AC-174 remain exactly as frozen in v107; v108..v112 are spec
  repairs that must not re-price the milestone.