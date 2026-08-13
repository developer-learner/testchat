# ERD-DELTA — spec v101 model dropdown dedup lock (consolidation)

Consolidation freeze: this milestone pins the model-dropdown dedup that the
`2ebd2bd` direct fix (dedup the dropdown's option list by id, 2026-08-13,
D-132 routing) shipped. No app behavior changes in this delta — the fix is
on the tree; this freeze adds the acceptance criterion and the UI oracle
that prove the dropdown renders exactly one option per model id, clearing
the regression-test gap left when the direct fix crossed the lane.

## Changed acceptance criteria

* **AC-167 — model dropdown dedup:** WHEN the model dropdown is populated
  from both the models list and the script-model catalog, THE SYSTEM SHALL
  render exactly one option per model id, even when the same id is present
  in both sources, such that a loaded script model is never offered twice
  and the dropdown never contains duplicate entries for the same model.

## Superseded acceptance criteria

None. AC-167 documents behavior that shipped in `2ebd2bd`; no earlier AC is
replaced.

## Changed files

* `src/static/catalog.js` — the model dropdown's owning file (per
  `contracts.ui` attribution for `model-select` and `eject-model-btn`); no
  code changes in this delta — the delta declares the ownership of the
  dedup that already ships.

## Test-to-file mapping

Now-approved node IDs pin exactly:

* `tests/test_ui_catalog.py::test_model_dropdown_shows_each_script_model_once[chromium]` (NEW — fresh oracle for the shipped dedup)
  -> `src/static/catalog.js` (AC-167)

The oracle routes both sources (`/api/v1/models` and `/api/v1/models/catalog`)
with the same model id present, opens the page, and counts the dropdown's
options via a JS evaluate on the locked `model-select` testid — exactly one
option for the overlap id and for a catalog-only id.

Contracts: `files` gains `src/static/catalog.js` (the new oracle's owner);
no entry_points, routes, schemas, errors, ui, externals, or smoke checks
change.