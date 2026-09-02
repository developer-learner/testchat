# ERD-DELTA v119 — restore the pending chat task to the coder lane

Freeze context: v117 installed the missing catalog acceptance signal and v118
successfully produced a mechanically synthesized, gate-valid eight-task plan.
The v117 bookkeeping freeze classified all inventory files as no-edit, which
incorrectly carried `src/api/chat.py` into the acceptance-only lane even though
the v116 AC-179 implementation is still pending. The shell therefore ran the
failing T3 oracle without invoking a coder. This delta corrects only that lane
classification.

## Design

- Declare `src/api/chat.py` as the sole `changed_files` member so the coder can
  apply the v116 message-less-error fix.
- Keep the other seven active inventory files in `no_edit_files`; their mapped
  tests and smoke checks remain acceptance-only.
- Preserve the complete v118 briefs, DAG, mappings, contracts, and frozen tests
  unchanged. No behavior or implementation instruction changes.

## Changed acceptance criteria

- None. AC-178/AC-179/AC-180 remain exactly as frozen in v115/v116.

## Superseded acceptance criteria

- None.

## Changed files

- `src/api/chat.py` (UPDATED, carried implementation): restore it to the coder
  lane so the already-frozen v116/v118 T3 brief can be executed.
- `src/services/models.py`, `src/api/models.py`, `src/static/catalog.js`,
  `src/services/storage.py`, `src/api/threads.py`, `src/static/threads.js`, and
  `src/static/app.js` remain explicit no-edit acceptance carries.

## Test-to-file mapping

* `tests/test_router_route.py::test_chat_internal_path_untouched_when_vortex_url_unset` -> `src/api/chat.py`
* `tests/test_router_route.py::test_chat_router_404_race_surfaces_not_ready_message` -> `src/api/chat.py`
* `tests/test_router_route.py::test_chat_router_error_while_still_ready_is_generic` -> `src/api/chat.py`
* `tests/test_router_route.py::test_chat_router_model_not_listed_falls_through_to_local_path` -> `src/api/chat.py`
* `tests/test_router_route.py::test_chat_router_model_router_down_falls_through_to_local_path` -> `src/api/chat.py`
* `tests/test_router_route.py::test_chat_routes_router_model_to_router_endpoint_and_passes_model` -> `src/api/chat.py`
