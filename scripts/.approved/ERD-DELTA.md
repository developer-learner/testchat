# ERD-DELTA — spec v99 quarantine-failure visibility and single-owner hydration

This milestone closes the two delta-scoped P1 findings of the 2026-08-09
PM review of spec v98: (1) a quarantine rename failure in storage was
silently reported as healthy empty history, and (2) the load-path
quarantine indicator could be erased by a racing writer. It is limited to
propagation of quarantine failure and single-owner hydration status. Model
lifecycle, process ownership, CSRF, source-URL validation, settings UX,
documentation drift, and accessibility findings remain outside this slice.

## Changed acceptance criteria

* **AC-161 — quarantine-failure visibility:** when the quarantine rename
  of a corrupt primary fails, `load_versioned_snapshot` raises
  `SnapshotUnavailableError` and GET `/api/v1/threads` returns
  `503 {"detail": "snapshot unavailable"}`, such that broken storage is
  never reported as healthy empty history and the UI keeps the hydration
  retry warning instead of creating replacement state.
* **AC-162 — single-owner hydration status:** app.js's hydration GET is
  the only writer of the `history-status` element, rendering
  `history unreadable (backup kept)` when the response carries
  `quarantined: true`, such that the load-path quarantine indicator can
  never be erased or double-written by a racing script.

## Superseded acceptance criteria

None. AC-156..160 remain the contract. The quarantine rename-failure path
is now an error (503) instead of a silent healthy-empty read, and the
`history-status` element has exactly one owner; both behaviors were
previously unpinned.

## Changed files

* `src/services/storage.py` — `load_versioned_snapshot` raises
  `SnapshotUnavailableError` when the quarantine rename fails; a successful
  quarantine keeps returning `([], 0)`. Signature unchanged.
* `src/api/threads.py` — the GET handler maps `SnapshotUnavailableError`
  to `503 {"detail": "snapshot unavailable"}`.
* `src/static/app.js` — hydration success renders the quarantine indicator
  from the response's `quarantined` field (single owner); failure keeps the
  retry warning.
* `src/static/threads.js` — the script-eval GET that wrote `history-status`
  is removed (app.js is now the single owner).

DAG: unchanged — `src/api/threads.py` depends on `src/services/storage.py`.
The browser tasks read survivors back through the GET handler, so
`src/static/threads.js` and `src/static/app.js` depend on the backend GET.
Task order: T1 (storage) -> T2 (threads.py) -> T4 (threads.js) -> T3
(app.js); keep T2 atomic.

## Coder briefs (verbatim)

### T1 — src/services/storage.py (AC-161, storage seam)

Implementation constraints: `src/services/storage.py`. Keep the exact
signature `def load_versioned_snapshot(validator=None) -> tuple[list[dict], int]`.
Do NOT add a path parameter and do NOT change what any caller passes. The data
path is read inside the function via the existing `_data_path()` helper.
`save_versioned_snapshot(threads: list[dict], expected_revision: int) -> int`,
`load_snapshot`, `save_snapshot`, `quarantine_files()`, and `SnapshotConflict`
are unchanged.

Define a module-level exception class `SnapshotUnavailableError(Exception)`
in this file.

Behavioral specification — inside `load_versioned_snapshot`, the current
implementation already renames the primary to `f"{path}.corrupt-{stamp}"`
with `stamp = time.strftime("%Y%m%d-%H%M%S")` on every quarantine path:
unreadable JSON, validator raising, validator returning False, and unreadable
shape. Keep that behavior and keep returning `([], 0)` when the rename
succeeds. NEW: in each of those four paths, when `os.rename` raises `OSError`,
keep the warning log and then `raise SnapshotUnavailableError from rename_exc`
instead of falling through to `return [], 0` — the caller must learn the
snapshot is unavailable, never see broken storage as healthy empty. The
validator is called exactly once with the WHOLE parsed document
(`validator(data)` — a dict envelope `{"revision": N, "threads": [...]}` or
a legacy list).

The `corrupt-` rename must appear within the first 30 lines of the function
body (a frozen smoke check greps 30 lines after the `def` line).

Acceptance: the storage smoke check is green, `quarantine_files()` finds a
`threads.json.corrupt-*` file after a successful schema-invalid quarantine,
and `test_quarantine_rename_failure_is_unavailable` passes.

### T2 — src/api/threads.py (AC-161, GET wrapper; response shape)

Implementation constraints: `src/api/threads.py`. This task owns all three `/api/v1/threads` route contracts (`route:GET`,
`route:PUT`, `route:DELETE`), plus the persistence oracles that exercise
them (`tests/test_persistence_revisions.py`,
`tests/test_websearch_api.py::test_put_threads_roundtrips_sources`,
`tests/test_threads_api.py`). None belong to any other task. Use the existing
models `ThreadsListResponse`, `ThreadsPayload`, `ThreadsRevisionPrecondition`,
`ThreadSnapshot`; import `load_versioned_snapshot`, `save_versioned_snapshot`,
`SnapshotUnavailableError` from `src.services.storage`.

In the GET `/api/v1/threads` handler, define a helper
`def _validate_snapshot_document(document) -> bool`: for a dict envelope
select `document.get("threads")` (raise `ValueError` if not a list); for
a list use it directly. Apply `ThreadSnapshot.model_validate(item)` to
EVERY item — a pydantic `ValidationError` (a `ValueError` subclass) is
raised when an item's shape is invalid, including nested roles such as
`role: "system"`. End with an explicit `return True`.
Call `threads, revision = load_versioned_snapshot(validator=_validate_snapshot_document)`.
NEVER pass `ThreadSnapshot.model_validate` itself — storage calls the
validator with the WHOLE document, so the envelope always fails and
quarantines every load.
`quarantined = bool(quarantine_files())` — never from `([], 0)`.
Return `ThreadsListResponse(threads=threads, revision=revision, quarantined=quarantined).model_dump(exclude_none=True)` — the response MUST be dumped with `exclude_none=True` so stored messages without `sources` stay without that key (frozen oracle: `'sources' not in message`).

NEW: wrap the `load_versioned_snapshot` call so a raised
`SnapshotUnavailableError` returns
`JSONResponse({"detail": "snapshot unavailable"}, status_code=503)` —
broken storage, never a healthy-empty read.

The PUT and DELETE handlers must be left EXACTLY as they are (role 422s,
`exclude_none` serialization, `ThreadSnapshot(**item)` re-validation,
409 revision-conflict, `{"status": "ok", "revision": N}`). Do NOT rewrite
or reformat them; the file may already satisfy this brief. If it does,
reply with exactly `=== NO CHANGES ===`.

Acceptance: GET returns `{"threads": [], "revision": 0, "quarantined": true}`
for a schema-invalid snapshot (moved to exactly one `*.corrupt-*` file
byte-for-byte) and `503` when the quarantine rename cannot complete; the
persistence, revision-conflict, and roundtrip oracles all pass.

### T3 — src/static/app.js (AC-158/159/162, hydration; single owner)

Implementation constraints: `src/static/app.js`. The element with
`id="status-history"` / `data-testid="history-status"` already exists in
`index.html`. Do not touch the mutation-queue code in `threads.js`.

Behavioral specification — replace the current initial-load `fetch`
chain (the `.then`/`.catch` at the bottom of the app boot):

1. Issue GET `/api/v1/threads` for hydration. The retry loop is a
   self-scheduling function: at the START of EVERY iteration, BEFORE issuing
   the fetch, write the warning text to the `history-status` element. This
   re-asserts the warning on every retry.
2. On failure (network error or non-ok status, including 503), the catch
   keeps the warning text exactly `history unavailable — retrying` (already
   written at the top of this iteration) and schedules the next retry via a
   short `setTimeout` loop. Do NOT call `Threads.createThread()` on failure
   — revision is unknown, so creating replacement state could destroy
   survivors.
3. On success: set the `history-status` text to the single-owner value
   `data.quarantined ? 'history unreadable (backup kept)' : ''` — the
   hydration response is now the ONLY source for this element. Install the
   revision FIRST via the existing
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
replaced by the quarantine indicator only when `quarantined` is true, the
seeded thread renders, and a subsequent new-thread mutation PUTs with the
hydrated revision.

### T4 — src/static/threads.js (AC-156/157/162, delete verb; single owner)

Implementation constraints: `src/static/threads.js`. Do not change the PUT
queue, the DELETE route handler's use, or any other behavior. This task does
NOT own `route:PUT /api/v1/threads` or any backend route — those belong to
the threads.py task; do not claim them.

Behavioral specification: (1) confirming a single row deletion
(`deleteThread(id)`) must remove only that thread and enqueue a revisioned
PUT whose payload is the complete survivor snapshot via the existing
`_enqueueMutation('PUT', { threads: _captureSnapshot() })` — never the
clear-all DELETE route. (2) REMOVE the standalone script-eval block at the
bottom of the file that issues its own `fetch('/api/v1/threads')` and writes
the `history-status` element (the load-path quarantine indicator) — app.js's
hydration GET is now the single owner of that element and renders
`history unreadable (backup kept)` from `data.quarantined`. Delete that
entire block: the fetch, both `.then` handlers, and the `.catch`.

Acceptance: deleting one of three threads issues one PUT (status 200, not a
DELETE), after a reload only the two survivors render and persist, and no
`fetch('/api/v1/threads')` call remains outside app.js.

## Test-to-file mapping

Now-approved node IDs pin exactly:

* `tests/test_data_safety_storage.py::test_valid_json_with_invalid_thread_schema_is_quarantined`
  -> `src/api/threads.py` (AC-160; after storage).
* `tests/test_storage_service.py::test_quarantine_rename_failure_is_unavailable`
  -> `src/services/storage.py` (AC-161; NEW this delta — all four quarantine
  paths raise `SnapshotUnavailableError` on rename failure).
* `tests/test_data_safety_ui.py::test_delete_one_thread_survives_reload[chromium]`
  -> `src/static/threads.js` (AC-156/157; after threads.py — the reload
  reads survivors back through the GET handler).
* `tests/test_data_safety_ui.py::test_hydration_failure_warns_retries_and_recovers_saving[chromium]`
  -> `src/static/app.js` (AC-158/159/162; after threads.js).

The 503 response shape is pinned by the T2 brief (the storage raise is
frozen; its UI consequence — retry warning, no replacement state — is
already pinned by the AC-158 hydration oracle for any non-ok GET).
Contracts: `entry_points` gains `src.services.storage:SnapshotUnavailableError`;
`errors` gains `error:503-snapshot-unavailable` (`status` 503,
`src/api/threads.py`). Existing smokes are unchanged.
