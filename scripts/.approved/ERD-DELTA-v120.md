# ERD-DELTA v120 — register the carried router acceptance mappings (bookkeeping)

Freeze context: the durable completion baseline is v119 (router recut complete,
`[success]` at spec v119). Seven frozen `test_router_route.py` node-ids are
pinned to their owner files only in the v115/v119 delta stack, not in the
standing `contracts.test_mapping`; and `schema:ModelInfo`'s documented `source`
literal never caught up to the frozen code (which already carries
`Flash_Q2KXL`, `Flash_IQ3XXS`, and `router`). This is an acceptance-bookkeeping
repair only — it changes no implementation, endpoint, route, product behavior,
or test bytes. It promotes the already-frozen router acceptance signals into
the standing spec so they survive the v121 standing-ERD consolidation, and
trues the `ModelInfo` schema documentation to the frozen `Literal`.

## Design

- Correct the existing `schema:ModelInfo` `source` field to state the frozen
  `Literal` verbatim: `'lmstudio' or 'nemotron' or 'deepseek-v4-flash-0731' or
  'Flash_Q2KXL' or 'Flash_IQ3XXS' or 'router'`. Documentation truing only; the
  pydantic model in `src/api/models.py` is unchanged.
- Register the seven carried `tests/test_router_route.py` ownership mappings in
  `contracts.test_mapping`: the three `is_router_model` / `ROUTER_MODEL_ID`
  tests to `src/services/models.py`, and the four `chat_router` fall-through /
  404-race tests to `src/api/chat.py`. These node-ids are already frozen and
  passing; this makes their file ownership mechanically visible to the task
  gate rather than carried only in the retiring delta stack.
- All eight source files are explicit no-edit acceptance carries for this
  bookkeeping freeze; no coder edit is declared.

## Changed acceptance criteria

- None. AC-175..AC-181 stand as frozen; this freeze makes their existing
  router acceptance signals mechanically visible and trues one schema doc
  string. It introduces no new behavior.

## Superseded acceptance criteria

- None.

## Changed files

- No implementation file changes in v120.
- `scripts/.approved/contracts.json` corrects the `schema:ModelInfo` `source`
  documentation to the frozen `Literal` and registers the seven carried
  `tests/test_router_route.py` ownership mappings. All eight source files are
  explicit no-edit acceptance carries.

## Test-to-file mapping

* `tests/test_router_route.py::test_is_router_model_true_for_any_ready_id`
  -> `src/services/models.py`
* `tests/test_router_route.py::test_is_router_model_false_when_not_listed_or_down`
  -> `src/services/models.py`
* `tests/test_router_route.py::test_router_model_id_constant_retired`
  -> `src/services/models.py`
* `tests/test_router_route.py::test_chat_router_model_not_listed_falls_through_to_local_path`
  -> `src/api/chat.py`
* `tests/test_router_route.py::test_chat_router_model_router_down_falls_through_to_local_path`
  -> `src/api/chat.py`
* `tests/test_router_route.py::test_chat_router_404_race_surfaces_not_ready_message`
  -> `src/api/chat.py`
* `tests/test_router_route.py::test_chat_router_error_while_still_ready_is_generic`
  -> `src/api/chat.py`
