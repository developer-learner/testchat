# ERD-DELTA v118 — deterministic planning bridge for the v106–v117 active range

Freeze context: the durable completion baseline remains v105, while the
active v106–v117 range contains the already-landed router work and the still
pending v116 `src/api/chat.py` correction. Repeated historical briefs make
the model-facing packet exceed its planning budget. This is a planning-only
repair: it changes no product behavior, tests, acceptance criteria, or API
contract. It restates one concise, authoritative coder brief per active file,
the complete DAG, and the ownership mapping so the orchestrator can synthesize
the plan mechanically without an EM call.

## Design

- Preserve the eight-file active inventory required by the skipped-freeze
  range. Seven files require no further code edit; their accepted behavior is
  verified by mapped tests or frozen smoke checks.
- `src/api/chat.py` retains the v116 correction: message-less `("error",)`
  items are handled in the stream loop and re-probe Vortex readiness.
- Use the `src/static/catalog.js` smoke check frozen in v117 so every inventory
  task has an acceptance signal even when static test collection omits
  Playwright's `[chromium]` parametrization suffix.
- The briefs below supersede earlier active-range brief text for planning
  purposes only. Earlier acceptance criteria and frozen tests remain binding.

## Changed acceptance criteria

- None. AC-175 through AC-181 remain unchanged from v115/v116.

## Superseded acceptance criteria

- None. This planning bridge changes decomposition instructions only.

## Changed files

- No implementation file is newly declared changed by v118.
- `src/api/chat.py` remains the unfinished implementation work carried from
  v116. The other seven inventory files are verification-only.
- No contract or test changes. The v117 catalog smoke signal remains frozen.

## Coder briefs (verbatim)

### T1 — src/services/models.py

Do not edit `src/services/models.py`. The dynamic Vortex ready-set recut is
already implemented: no fixed router model id exists, the live probe uses a
5-second timeout, results are deduplicated in probe order, and router models
are appended to the models list. Acceptance: leave the file byte-identical;
its mapped router tests must pass.

### T2 — src/api/models.py

Do not edit `src/api/models.py`. Its model-list and catalog routes already
expose the service results with the accepted router source schema. Acceptance:
leave the file byte-identical; its mapped router API tests must pass.

### T3 — src/api/chat.py

Edit only `src/api/chat.py`; do not change routing, imports, token/think/done
handling, or any other file. `stream_reply()` reports transport failure as a
message-less `("error",)` item, so the primary fix belongs in the stream
loop's existing `elif item[0] == "error":` branch, not only in the outer
exception handler.

Inside `event_generator`, compute once:
`routed_to_router = endpoint_override is not None and endpoint_override == models_mod.router_chat_endpoint()`.
Add a small local helper for message-less errors. It returns
`Model {request.model} is not ready in Vortex. Pick a local model or retry once it is loaded.`
when the request was router-routed, `request.model` is not `None`, and a fresh
`models_mod.is_router_model(request.model)` call is false; otherwise it returns
`llm_mod.FALLBACK_REPLY`.

In the stream-loop error branch, preserve `item[1]` exactly when present; only
when `len(item) == 1` use the helper. In the outer
`except (ConnectionError, TimeoutError, OSError) as e`, preserve `str(e)` when
non-empty; only a message-less exception uses the same helper. JSON-encode the
selected message and retain the existing SSE error shape. Acceptance: the 404
race emits the exact Vortex not-ready message; still-ready, non-router, and
message-bearing errors retain their prior results.

### T4 — src/static/catalog.js

Do not edit `src/static/catalog.js`. Its existing models-list/catalog merge
already turns every models-list entry, including a router entry, into one
loaded non-script option. Acceptance: leave the file byte-identical and pass
its frozen smoke check.

### T5 — src/services/storage.py

Do not edit `src/services/storage.py`. It is carried only as a previously
accepted behavioral owner. Acceptance: leave the file byte-identical and pass
its frozen smoke check.

### T6 — src/api/threads.py

Do not edit `src/api/threads.py`. It is carried only as a previously accepted
behavioral owner. Acceptance: leave the file byte-identical and pass its
frozen smoke check.

### T7 — src/static/threads.js

Do not edit `src/static/threads.js`. It is carried only as a previously
accepted behavioral owner. Acceptance: leave the file byte-identical and pass
its frozen smoke check.

### T8 — src/static/app.js

Do not edit `src/static/app.js`. It is carried only as a previously accepted
behavioral owner. Acceptance: leave the file byte-identical and pass its
frozen smoke check.

## Task DAG

`src/api/models.py` depends on `src/services/models.py`.
`src/api/chat.py` depends on `src/services/models.py`.
`src/api/chat.py` depends on `src/api/models.py`.
`src/static/catalog.js` depends on `src/services/models.py`.
`src/static/catalog.js` depends on `src/api/models.py`.
`src/static/catalog.js` depends on `src/api/chat.py`.
`src/services/storage.py` depends on `src/static/catalog.js`.
`src/api/threads.py` depends on `src/services/storage.py`.
`src/static/threads.js` depends on `src/api/threads.py`.
`src/static/app.js` depends on `src/static/threads.js`.

## Test-to-file mapping

* `tests/test_router_route.py::test_is_router_configured_reflects_env` -> `src/services/models.py`
* `tests/test_router_route.py::test_is_router_model_false_when_not_listed_or_down` -> `src/services/models.py`
* `tests/test_router_route.py::test_is_router_model_true_for_any_ready_id` -> `src/services/models.py`
* `tests/test_router_route.py::test_router_chat_endpoint_uses_vortex_url` -> `src/services/models.py`
* `tests/test_router_route.py::test_router_model_id_constant_retired` -> `src/services/models.py`
* `tests/test_router_route.py::test_router_models_deduplicated` -> `src/services/models.py`
* `tests/test_router_route.py::test_router_models_empty_when_probe_raises` -> `src/services/models.py`
* `tests/test_router_route.py::test_router_models_empty_when_router_503` -> `src/services/models.py`
* `tests/test_router_route.py::test_router_models_empty_when_router_omits_it` -> `src/services/models.py`
* `tests/test_router_route.py::test_router_models_empty_when_vortex_url_unset` -> `src/services/models.py`
* `tests/test_router_route.py::test_router_models_included_in_list_models` -> `src/services/models.py`
* `tests/test_router_route.py::test_router_models_lists_router_when_router_reports_it` -> `src/services/models.py`
* `tests/test_router_route.py::test_get_models_includes_router_when_ready` -> `src/api/models.py`
* `tests/test_router_route.py::test_router_model_never_in_catalog` -> `src/api/models.py`
* `tests/test_router_route.py::test_chat_internal_path_untouched_when_vortex_url_unset` -> `src/api/chat.py`
* `tests/test_router_route.py::test_chat_router_404_race_surfaces_not_ready_message` -> `src/api/chat.py`
* `tests/test_router_route.py::test_chat_router_error_while_still_ready_is_generic` -> `src/api/chat.py`
* `tests/test_router_route.py::test_chat_router_model_not_listed_falls_through_to_local_path` -> `src/api/chat.py`
* `tests/test_router_route.py::test_chat_router_model_router_down_falls_through_to_local_path` -> `src/api/chat.py`
* `tests/test_router_route.py::test_chat_routes_router_model_to_router_endpoint_and_passes_model` -> `src/api/chat.py`
* `tests/test_ui_catalog.py::test_model_dropdown_lists_router_model_from_models_list` -> `src/static/catalog.js`
* `tests/test_storage_service.py::test_roundtrip_preserves_snapshot` -> `src/services/storage.py`
* `tests/test_data_safety_storage.py::test_valid_json_with_invalid_thread_schema_is_quarantined` -> `src/api/threads.py`
* `tests/test_data_safety_ui.py::test_delete_one_thread_survives_reload` -> `src/static/threads.js`
* `tests/test_data_safety_ui.py::test_hydration_failure_warns_retries_and_recovers_saving` -> `src/static/app.js`
