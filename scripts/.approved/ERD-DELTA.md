# ERD-DELTA — spec v100 settings-save failure visibility (lock alignment)

Consolidation freeze: this milestone locks the settings-save failure surface
that the `7bfc622` direct fix (model-lifecycle reliability, 2026-08-09, after
spec v99 froze) shipped, and that `tests/test_ui_settings.py` already pins.
No app behavior changes in this delta — the element ships; this freeze brings
the spec's lock and the PRD's AC numbering into line with the frozen oracle,
clearing the INV-4 halt that blocked spec v100 (the test observed testid
`settings-status`, absent from `contracts.ui` since the value entered the
tree outside the freeze lane). The test file is restaged for provenance
correction only (its docstring cited freeze versions that never occurred).

## Changed acceptance criteria

* **AC-166 — settings-save failure visibility:** WHEN the user saves the
  system prompt via the settings modal and the save request fails, THE SYSTEM
  SHALL keep the settings modal open and display the failure notice
  ``Save failed`` in the modal's ``settings-status`` element, such that the
  user is never left believing the system prompt was saved. The notice text
  is pinned verbatim by the frozen UI oracle; the modal stays interactive
  (the Save button remains visible).

## Superseded acceptance criteria

None. AC-166 documents behavior that shipped in `7bfc622`; no earlier AC is
replaced.

## Changed files

* `src/static/chrome.js` — the settings modal's owning file (per
  `contracts.ui` attribution alongside `settings-toggle`, `settings-save`,
  `settings-cancel`); no code changes in this delta — the delta declares the
  lock and ownership of the element that already ships.

## Test-to-file mapping

Now-approved node IDs pin exactly:

* `tests/test_ui_settings.py::test_settings_save_failure_keeps_the_modal_open_and_is_visible[chromium]` (UPDATED — provenance correction only, no behavioral change)
  -> `src/static/chrome.js` (AC-166)

The docstring's earlier ``spec v100; v101 and v102 re-freezes restaged this
file`` citation was fiction — the file entered the tree with the `7bfc622`
direct fix and was pinned by the `f569528` INV-1 bookkeeping commit; this
freeze restages it so the accepted AC reference is real and the provenance
truthful.

Contracts: ``ui`` gains ``ui:settings-status`` (testid ``settings-status``,
file ``src/static/chrome.js``). No entry_points, routes, schemas, errors,
externals, or smoke checks change.