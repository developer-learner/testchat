# ERD-DELTA v117 — expose the carried catalog acceptance signal

Freeze context: the durable completion baseline is v105 and the active
v106–v116 range still includes `src/static/catalog.js`. The frozen router UI
test was originally collected with a `[chromium]` suffix, while the current
static fallback records its bare function id; consequently that historical
test does not enter the active function-granular slice and T4 has neither a
runnable mapped test nor a smoke signal. This is an acceptance-bookkeeping
repair only. It changes no implementation, endpoint, schema, or product
behavior.

## Design

- Clarify the existing `ui:model-select` contract with the already-frozen
  behavior: ids returned by the models list, including router ids, are merged
  by id with the catalog and rendered once as loaded non-script choices.
- Add a `src/static/catalog.js` smoke check for the exact established merge
  call that makes models-list entries loaded non-script options.
- Keep all eight active-range files in the inventory as explicit no-edit
  acceptance carries. The unfinished `src/api/chat.py` implementation remains
  owned by the earlier v116 delta; v117 itself declares no new coder edit.

## Changed acceptance criteria

- None. This makes the existing router-picker acceptance mechanically visible
  to the task gate; it introduces no new behavior.

## Superseded acceptance criteria

- None.

## Changed files

- No implementation file changes in v117.
- `scripts/.approved/contracts.json` updates `ui:model-select` documentation
  and adds the `src/static/catalog.js` smoke signal. All eight source files are
  explicit no-edit acceptance carries for this bookkeeping freeze.

## Test-to-file mapping

* `tests/test_ui_catalog.py::test_model_dropdown_lists_router_model_from_models_list` -> `src/static/catalog.js`
