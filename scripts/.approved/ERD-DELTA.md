# ERD-DELTA — spec v93 validator correction: conversation data safety

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

* `src/static/threads.js` — AC-156/157: ordered PUT persists survivors;
  never DELETE `/api/v1/threads`; hydration owns `history-status`.
* `src/static/app.js` — AC-158/159: failed GET warns/retries; success installs
  threads + revision before mutation; later PUTs adopt response revision.
* `src/services/storage.py` — `load_versioned_snapshot(validator=None)`
  quarantines schema-invalid primary exactly to `<primary>.corrupt-<timestamp>`
  and returns `([], 0)`; valid reads keep revision. Signature unchanged:
  no path parameter, `_data_path()` is read inside the function.
* `src/api/threads.py` — GET's wrapper selects `document["threads"]` for an
  envelope or the legacy list, then applies `ThreadSnapshot.model_validate` to
  EVERY item, including nested roles. Never pass that method directly. Unpack
  the versioned result; `quarantined = bool(quarantine_files())`, never
  `([], 0)`.

DAG: `src/api/threads.py` depends on `src/services/storage.py`; keep T2 atomic.
The browser files remain orderable, with app.js acceptance assuming threads.js
hydration-status ownership.

## Coder briefs (verbatim)

### T1 — src/services/storage.py (AC-160, storage seam)

Implementation constraints: `src/services/storage.py`. Keep the exact
signature `def load_versioned_snapshot(validator=None) -> tuple[list[dict], int]`.
Do NOT add a path parameter and do NOT change what any caller passes. The data
path is read inside the function via the existing `_data_path()` helper.
`save_versioned_snapshot(threads: list[dict], expected_revision: int) -> int`,
`load_snapshot`, `save_snapshot`, `quarantine_files()`, and `SnapshotConflict`
are unchanged.

Behavioral specification — inside `load_versioned_snapshot`, replace the
current quarantine mechanism (`_quarantine_file`, which renames to the
`.quarantine` suffix) so that every quarantine path in this function:

1. Renames the primary file to exactly `f"{path}.corrupt-{stamp}"` where
   `stamp = time.strftime("%Y%m%d-%H%M%S")` (the `time` module is already
   imported), matching the `*.corrupt-*` glob `quarantine_files()` lists.
2. Renames BEFORE returning, and returns `([], 0)` after the rename.
3. Logs `logger.warning` with primary/corrupt/error in the message when the
   rename itself fails (pattern already present), and still returns `([], 0)`.

The quarantine paths in this function are: unreadable JSON
(`json.JSONDecodeError`/`ValueError`/`OSError` on parse); the validator
raising `ValueError`; the validator returning `False` (add this case —
currently only the exception path exists); and an unreadable non-dict,
non-list shape.

The validator is called exactly once with the WHOLE parsed document
(`validator(data)` — a dict envelope `{"revision": N, "threads": [...]}` or a
legacy list). Do not slice or pre-validate in this function.

The `corrupt-` rename must appear within the first 30 lines of the function
body (a frozen smoke check greps 30 lines after the `def` line).

Acceptance: the storage smoke check is green and `quarantine_files()` finds a
file whose name starts with `threads.json.corrupt-` after a schema-invalid
snapshot is loaded.

### T2 — src/api/threads.py (AC-160, GET wrapper)

Implementation constraints: FastAPI route handlers in `src/api/threads.py`.
Use the existing models `ThreadsListResponse`, `ThreadsPayload`,
`ThreadsRevisionPrecondition`, `ThreadSnapshot`. Import
`load_versioned_snapshot` and `save_versioned_snapshot` from
`src.services.storage`. Do not change the PUT or DELETE handler logic.

Behavioral specification:

1. In the GET `/api/v1/threads` handler, define a module-level helper
   `def _validate_snapshot_document(document) -> bool` (or reuse/extend the
   existing `_validate_snapshot`/`_validate_thread_snapshot` helpers into one)
   that:
   a. If `document` is a dict envelope, selects the `threads` list
      (`document.get("threads")`); if it is not a list, raises `ValueError`.
   b. If `document` is a list, uses it directly.
   c. Applies `ThreadSnapshot.model_validate(item)` to EVERY item in the
      list — this raises pydantic `ValidationError` (a `ValueError`
      subclass) when an item's shape is invalid, including nested message
      roles such as `role: "system"` that `ThreadSnapshot` rejects.
   d. Returns `True` only when every item validates.
2. Call `threads, revision = load_versioned_snapshot(validator=_validate_snapshot_document)`.
   NEVER pass `ThreadSnapshot.model_validate` itself as the validator
   argument — the storage layer calls it with the WHOLE document, so the
   envelope dict would always fail validation and quarantine every load.
3. Compute `quarantined = bool(quarantine_files())` — never derive it from
   the `([], 0)` return.
4. Return `ThreadsListResponse(threads=threads, revision=revision, quarantined=quarantined)`.

Acceptance: with a schema-invalid snapshot present, GET returns
`{"threads": [], "revision": 0, "quarantined": true}` and the primary file is
moved to exactly one `*.corrupt-*` file byte-for-byte.

### T3 — src/static/app.js (AC-158/159, hydration)

Implementation constraints: `src/static/app.js`. The element with
`id="status-history"` / `data-testid="history-status"` already exists in
`index.html`. Do not touch the PUT/DELETE queue code in `threads.js`.

Behavioral specification — replace the current initial-load `fetch`
chain (the `.then`/`.catch` at the bottom of the app boot):

1. Issue GET `/api/v1/threads` for hydration.
2. On failure (network error or non-ok status), set the `history-status`
   element's text to exactly `history unavailable — retrying` and retry the
   GET automatically (a short `setTimeout` loop is fine). Do NOT call
   `Threads.createThread()` on failure — revision is unknown, so creating
   replacement state could destroy survivors.
3. On success: clear the warning (set `history-status` text to `""`),
   install the revision FIRST via the existing
   `Threads.setHydratedRevision(data.revision != null ? data.revision : 0)`
   before any mutation can enqueue, then hydrate threads into the UI
   (existing logic: populate `TC.threads`, render the newest thread, render
   the sidebar; if there are no threads, `Threads.createThread()` as today).
4. Keep the retry loop running until a GET succeeds; each retry must
   originate from app.js code (a frozen UI oracle detects hydration GETs by
   the caller stack containing `/static/app.js`).

The literal string `history unavailable — retrying` must appear in this file
(frozen smoke check).

Acceptance: after a failed initial GET the `history-status` element shows
`history unavailable — retrying`; after the retry succeeds the warning is
cleared, the seeded thread renders, and a subsequent new-thread mutation PUTs
with the hydrated revision.

### T4 — src/static/threads.js (AC-156/157, delete verb)

Implementation constraints: `src/static/threads.js`. Do not change the PUT
queue, the DELETE route handler's use, or any other behavior.

Behavioral specification: confirming a single row deletion
(`deleteThread(id)`) must remove only that thread and enqueue a revisioned
PUT whose payload is the complete survivor snapshot via the existing
`_enqueueMutation('PUT', { threads: _captureSnapshot() })` — never the
clear-all DELETE route. If the file already satisfies this, reply with
exactly `=== NO CHANGES ===`.

Acceptance: deleting one of three threads issues one PUT (status 200, not a
DELETE), and after a reload only the two survivors render and persist.

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
signature plus `corrupt-`; the threads.py smoke now probes that the GET
handler no longer passes `ThreadSnapshot.model_validate` directly; existing
app/API smokes remain unchanged.
