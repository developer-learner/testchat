# ERD-DELTA — spec v92 validator correction: conversation data safety

This milestone repairs the three persistence defects identified in the
2026-08-08 audit. It is intentionally limited to exact-one deletion,
recoverable initial hydration, and quarantine of schema-invalid JSON. Model
lifecycle, process ownership, CSRF, source-URL validation, settings UX,
documentation drift, and accessibility findings remain outside this slice.

## Changed acceptance criteria

* **AC-156 — exact-one deletion:** confirming one row deletion removes only
  that thread and persists the complete survivor snapshot, such that reload
  returns all and only the survivors.
* **AC-157 — mutation verb boundary:** a row deletion uses the revisioned PUT
  queue and never the clear-all DELETE route, such that survivors cannot be
  replaced by an empty snapshot.
* **AC-158 — hydration failure visibility and retry:** a failed initial GET
  must write exactly `history unavailable — retrying` to `history-status`,
  retry automatically, and create no replacement state while revision is
  unknown.
* **AC-159 — hydration recovery:** a successful retry installs threads and
  revision before later writes and clears the warning, such that the next
  mutation and all survivors persist through reload.
* **AC-160 — schema-invalid quarantine:** valid JSON whose thread/message
  shape fails the PUT `ThreadSnapshot` model is quarantined byte-for-byte and
  read as `threads: []`, `revision: 0`, such that invalid state is neither
  served nor overwritten.

## Superseded acceptance criteria

None. AC-142 remains the contract for explicit clear-all, such that its
revision-precondition and empty-snapshot semantics are unchanged.
The standing unreadable-snapshot quarantine and backup-visibility behavior
remains unchanged. AC-156..160 close previously unpinned paths without
weakening those behaviors.

## Changed files

* `src/static/threads.js` — AC-156/157/158: ordered PUT persists survivors;
  never DELETE `/api/v1/threads`; hydration owns `history-status`.
* `src/static/app.js` — AC-158/159: failed GET warns/retries; success installs
  threads + revision before mutation; later PUTs adopt response revision.
* `src/services/storage.py` — `load_versioned_snapshot(validator=None)` passes
  the WHOLE parsed document (envelope dict or legacy list) once. False/raise
  moves the primary exactly to `<primary>.corrupt-<timestamp>` and returns
  `([], 0)`; valid reads keep revision.
* `src/api/threads.py` — GET's wrapper selects `document["threads"]` for an
  envelope or the legacy list, then applies `ThreadSnapshot.model_validate` to
  EVERY item, including nested roles. Never pass that method directly. Unpack
  the versioned result; `quarantined = bool(quarantine_files())`, never `([], 0)`.

DAG: `src/api/threads.py` depends on `src/services/storage.py`; keep T2 atomic.
The browser files remain orderable, with app.js acceptance assuming threads.js
hydration-status ownership.

## Test-to-file mapping

Now-approved node IDs pin exactly:

* `tests/test_data_safety_storage.py::test_valid_json_with_invalid_thread_schema_is_quarantined`
  -> `src/api/threads.py` (AC-160; after storage).
* `tests/test_data_safety_ui.py::test_delete_one_thread_survives_reload[chromium]`
  -> `src/static/threads.js` (AC-156/157).
* `tests/test_data_safety_ui.py::test_hydration_failure_warns_retries_and_recovers_saving[chromium]`
  -> `src/static/app.js` (AC-158/159).

Tests and mappings are unchanged. The backend oracle distinguishes healthy
empty storage (`quarantined: false`) from schema quarantine and pins the
`threads.json.corrupt-*` name. Storage smoke requires the versioned validator
signature plus `corrupt-`; existing app/API smokes remain unchanged.
