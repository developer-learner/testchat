# ERD-DELTA — spec v91 seam correction: conversation data safety

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

* `src/static/threads.js` — AC-156/157/158: post-delete survivors are
  enqueued via the ordered revisioned PUT; never DELETE `/api/v1/threads`;
  hydration alone owns `history-status`.
* `src/static/app.js` — AC-158/159: on failed GET write exact text and
  retry until success; a success installs threads + revision before mutation;
  later PUTs adopt response revision.
* `src/services/storage.py` — AC-160: the sole validated-read seam is
  `load_versioned_snapshot(validator=None) -> (list, revision)`. Under lock it
  applies the callback; JSON/shape failure is quarantined and returns `([], 0)`.
* `src/api/threads.py` — GET passes its `ThreadSnapshot` validator only to
  `load_versioned_snapshot`, unpacks `(threads, revision)`, and derives
  `quarantined` only from `bool(quarantine_files())`, never from `([], 0)`;
  thus healthy empty storage remains false and invalid state is not served.

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
empty storage (`quarantined: false`) from schema quarantine. The delete oracle
hovers its row; the hydration oracle counts only `app.js` GETs. Existing
`src/static/app.js` smoke still requires `history unavailable — retrying`.
