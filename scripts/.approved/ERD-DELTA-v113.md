# ERD-DELTA v113 — router model: T3 chat.py gate restored to the accepted implementation

Freeze context: standing spec v112 (probe timeout 2s -> 5s, applied and
committed at T1 [f565a71], T1 PASS). The v112 run's T3 gate failures are
conclusively diagnosed as CODER CORRUPTION, not defects in the spec, the
tests, or the probe budget:

- v112 T3 strike 1 (765b5bb): the coder removed the router-probe gate;
  "not listed" and "router down" started returning 200 instead of 422
  (gate evidence: `assert 200 == 422`).
- v112 T3 strike 2 (0b95a87 / 275e053): the coder substituted an env-level
  gate (`is_router_configured()`) for the probe-level gate
  (`is_router_model(request.model)`) and hoisted it out of the request.model
  guard, inverting three pinned outcomes at once: not-listed -> 200 (should
  be 422), router-down -> 200 (should be 422), and the unset-VORTEX_URL
  internal path -> 422 (should be 200, with endpoint_override untouched).
- The EM consult's "no change needed" revision was itself wrong: the
  corrupted file was already committed before the consult, so the EM
  validated the corruption.

Fix: v113 re-executes T3 with an exact, mechanical SEARCH/REPLACE repair
(small diff: restore the `elif` gate inside the request.model guard, using
the probe check). Nothing else changes: the probe-timeout fix stays in
src/services/models.py (committed f565a71); all other tasks unchanged; the
script-model branch above the router gate is untouched.

## Changed acceptance criteria

None. AC-170..AC-174 stand frozen since v107, unchanged.

## Superseded acceptance criteria

None.

## Changed files

- `src/api/chat.py` (edited: T3 re-execution) — one gate block restored to
  the accepted implementation (commit fb16089's semantics).
- `src/services/models.py`, `src/api/models.py` (edited, v107/v112) —
  unchanged by this freeze; T1/T2 land as "no change needed".
- `src/static/catalog.js`, `src/services/storage.py`, `src/api/threads.py`,
  `src/static/threads.js`, `src/static/app.js` (no_edit) — unchanged.
- `scripts/.approved/contracts.json` — unchanged content, erd_version 113.

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

No further change: the probe-timeout revision (2s -> 5s) is applied and
committed (f565a71); the full v107 seam set is accepted, mapped tests green.
Do not touch this file.

### T2 — src/api/models.py (router source in the models API)

No further change: accepted (83c15c4). Do not touch this file.

### T3 — src/api/chat.py (router chat branch — EXACT gate repair)

The current file is CORRUPTED (committed 275e053): the router gate was
hoisted out of the request.model guard and changed to an env-level check.
Repair it with ONE edit block as follows.

SEARCH (the corrupted hoisted gate; ensure the leading blank line and
indentation match the committed file exactly):

```
    if request.model == models_mod.ROUTER_MODEL_ID:
        if not models_mod.is_router_configured():
            raise HTTPException(
                status_code=422,
                detail=f"Model {request.model} is not available",
            )
        endpoint_override = models_mod.router_chat_endpoint()
```

REPLACED (the accepted gate, indented INSIDE the request.model guard —
the elif attaches to the script-model if above it):

```
        elif (
            models_mod.is_router_configured()
            and request.model == models_mod.ROUTER_MODEL_ID
        ):
            if not models_mod.is_router_model(request.model):
                raise HTTPException(
                    status_code=422, detail=f"Model {request.model} is not loaded"
                )
            endpoint_override = models_mod.router_chat_endpoint()
```

Rules: change ONLY this block; do not touch the script-model branch, the
prompt assembly, the generator, or any other file; do not reformat. After
the edit, verify in your reply that `is_router_model` appears in
src/api/chat.py and that `is_router_configured` does NOT appear in it.
If the SEARCH block does not match the committed file exactly, reply with
a full-file `=== FILE: src/api/chat.py ===` block whose router gate is the
REPLACED form above and everything else matches the committed file.

### T4 — src/static/catalog.js (router dropdown presence)

No code change. The existing fetchModels flow merges the models list and
the catalog by id; a list entry with id `qwen3.8-27b-8bit` and source
`router` renders as a selectable option without any edit. Acceptance: the
mapped browser test passes with no working-tree change to this file.

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

- The v112 T3 evidence is fully explained by the coder corruption described
  above (byte-level comparison against the accepted implementation); no
  residual flake remains unexplained.
- The REPLACED gate above is the exact accepted implementation (commit
  fb16089's src/api/chat.py lines 43-51); the probe-timeout revision lives
  in src/services/models.py and does not alter this file's correctness.
- EM consult-ability for T3 is redundant this round: the brief is a
  mechanical search-and-replace; if the gate still fails after two
  strikes, escalate with this reasoning in the bundle.
- AC-170..AC-174 remain exactly as frozen in v107; v108..v113 are spec
  repairs that must not re-price the milestone.
