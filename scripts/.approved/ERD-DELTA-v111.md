# ERD-DELTA v111 — router model: T3 escalation answered, zero content change

Freeze context: standing spec v110. The v110 run's T3 (src/api/chat.py router
branch) failed its mapped test
`test_chat_routes_router_model_to_router_endpoint_and_passes_model` with
`422 == 200` evidence across strikes, the coder reported no changes needed,
the EM brief revision did not help, and the task escalated as
`caps-exhausted` (bundle .pipeline-state/escalations/T3/bundle.md).

The TPM (this delta's author) re-verified the evidence against the frozen
tree at the exact commit the gate judged:

- host: `tests/test_router_route.py` 15/15 passed
  (`PYTHONPATH=. .venv/bin/pytest`),
- sandbox container (identical runner to the gate, `--rw .cache`,
  `pytest -p no:cacheprovider`): 15/15 passed; the four T3-mapped node-ids
  passed in isolation and in the full file.

The committed implementation of T1/T2/T3 (commits 910fdd0, 1950aa4, 83c15c4,
fb16089) matches the brief verbatim: the router branch sits inside
`if request.model:` after the script-model branch, gates on
`is_router_configured()` and `request.model == ROUTER_MODEL_ID`, raises the
exact 422 contract when not listed, and sets
`endpoint_override = router_chat_endpoint()` when listed. No spec defect
exists that the re-verification could identify; the gate's 422 evidence is
not reproducible on the frozen tree, so the classification is transient
container-state artifact (possible stale VM->host mount view during the
gate's verdict run), not a frozen-spec defect.

This freeze answers the escalation by the pipeline's own mechanism (D-31:
TPM answers return as a delta applied by refreeze.sh) and changes NOTHING:
AC-170..AC-174 stand exactly as frozen in v107, no application file
changes, no test bytes change, contracts registration (v109/v110) intact.

## Changed acceptance criteria

None. AC-170..AC-174 were introduced by v107 and remain in force unchanged.

## Superseded acceptance criteria

None.

## Changed files

- `src/services/models.py`, `src/api/models.py`, `src/api/chat.py`
  (edited, v107) — the router feature as frozen in v107..v110; unchanged by
  this freeze.
- `src/static/catalog.js`, `src/services/storage.py`, `src/api/threads.py`,
  `src/static/threads.js`, `src/static/app.js` (no_edit, carried-owner
  declarations) — unchanged.
- `scripts/.approved/contracts.json` (v109/v110 registration) — unchanged by
  this freeze; the staged overlay restates the identical content at erd
  version 111 so the merge is a byte-identical no-op.

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

Already implemented and accepted at v110 (commits 910fdd0/1950aa4): the
brief is unchanged. No further work; the mapped tests are green.

### T2 — src/api/models.py (router source in the models API)

Already implemented and accepted at v110 (commit 83c15c4): the brief is
unchanged. No further work; the mapped tests are green.

### T3 — src/api/chat.py (router chat branch)

Already implemented and accepted at v110 (commit fb16089); the v110 gate's
422 evidence is not reproducible (re-verified 4/4 in isolation and 15/15 in
the file, host and sandbox) and is classified as transient container-state
artifact. The brief is unchanged: the router branch must sit inside
`if request.model:` after the script-model branch; not listed -> the exact
422 contract; listed -> `endpoint_override = router_chat_endpoint()`; with
`VORTEX_URL` unset no id enters the branch. No further work.

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

- The escalation answer is "no defect": the gate's failing evidence cannot
  be reproduced on the frozen tree with the same runner, and the committed
  implementation matches the brief verbatim. If the milestone re-run fails
  T3 again with the same 422 evidence, the transient classification is
  wrong and the VM->host mount view during gate runs becomes the suspect —
  that investigation then belongs in the blueprint, not in another freeze.
- This delta is intentionally zero-content (nonbehavioral); its only
  function is to consume the T3 escalation through the pipeline's own
  D-31 mechanism and refresh the per-freeze counters.