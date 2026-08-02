ERD Delta — testchat M33 conflict-safe history persistence, v73 correction (erd_version 73)

## Changed acceptance criteria

v73 adds no numbered acceptance criterion: AC-136 through AC-148 remain
exactly as frozen in v72. This correction adds deterministic failure oracles
for existing AC-75 and AC-82 and removes implementation-location and locking
ambiguities. AC-35 and AC-37 remain constrained by mandatory revision preconditions.
AC-75 and AC-76 continue to govern ordinary save failures. AC-78, AC-79,
AC-80, AC-81, and AC-82 remain unchanged while their storage/API artifacts
adopt the revision envelope. Every other live v71 criterion remains in force,
including AC-111..AC-135.

No new numbered criterion is introduced. Backup-rotation failure is a failed
save under AC-75 and cannot satisfy AC-82; cleanup-error precedence preserves
that same failure's visibility rather than adding a new user capability.

## Superseded acceptance criteria

M8 flagged assumption A15, "Concurrent tabs are last-write-wins," is formally
superseded. No numbered acceptance criterion is retired. Standing prose that
describes fire-and-forget unordered replacement is superseded only to the
extent AC-136..AC-148 require revisioned, ordered persistence.

## Changed files

### `src/services/storage.py`

Public surface: keep `load_snapshot()` (list-only compatibility) and
`save_snapshot()`. Add `load_versioned_snapshot() -> tuple[list[dict], int]`,
`save_versioned_snapshot(threads, expected_revision) -> int`, and
`SnapshotConflict.current_revision`.

Read `{"revision": int, "threads": [...]}`. Missing primary is `([], 0)`.
A legacy raw list—including a `.bak` restored as primary—reads losslessly at
revision 0; its next accepted write stores envelope revision 1 and rotates the
raw primary to `.bak`. `load_snapshot()` returns only threads. Revisions are
monotonic integers, never content hashes.

One module-level non-reentrant lock covers read-current, compare, backup,
temp-write, atomic replace, and revision advance. Mismatch raises
`SnapshotConflict` before any directory/temp/backup/primary write. Match
always writes `expected + 1`, including equal PUT or empty DELETE, by
same-directory temp replacement; preserve quarantine and exactly one `.bak`.

Private `_save_versioned_snapshot_locked(threads, expected_revision)` assumes
the lock is held and performs compare/save. Public `save_versioned_snapshot`
acquires once, then calls it. Compatibility `save_snapshot` acquires once,
reads the generation under that lock, calls the private helper directly,
discards its revision, and returns compatibly. Never call the lock-acquiring
public save while holding the lock; never unlock between read and helper call.

Failure handlers are distinct:

1. If `shutil.copy2(primary, bak)` raises `OSError`, warn with primary path,
   backup path, and exception, then re-raise it. Outer failure handling removes
   temp and propagates that original error; primary bytes/revision stay fixed.
2. If temp unlink then fails, warn with the exact temp path and cleanup
   exception, but re-raise the ORIGINAL primary/backup error, never cleanup's.

### `src/api/threads.py`

Extend `ThreadsPayload` with required `revision: int >= 0`. Add a DELETE body
model containing required `revision: int >= 0`. GET performs one revisioned
load and returns `{"threads": [...], "revision": n, "quarantined": bool}`.
PUT calls `save_versioned_snapshot(payload.threads, payload.revision)`; DELETE
calls it with `[]`. Both return `{"status":"ok", "revision": n+1}`.

Map `SnapshotConflict` to HTTP 409 with the exact top-level JSON body
`{"error":"revision_conflict", "current_revision": n}`; do not wrap it in
FastAPI's `detail`. Validation failures remain 422 and write nothing.

### `src/static/threads.js`

Own the authoritative hydrated revision, ordered persist queue, and conflict
latch. Every persistence-worthy mutation captures its own complete snapshot
at enqueue time. Run at most one PUT at a time. The first request uses the
hydrated revision; after a 200, adopt the response revision before issuing the
next queued snapshot. Do not coalesce or reorder mutations.

Ordinary network/non-409 failures preserve AC-75/AC-76 (`not saved`) and do
not advance revision. A 409 clears pending snapshots, latches the page against
every later PUT/DELETE, and writes exactly `history changed elsewhere — reload
required` to `save-status`. Only document reload clears the latch. Expose the
minimum hook app.js needs to install the GET revision before a mutation can
enqueue.

### `src/static/app.js`

During startup GET hydration, install both `data.threads` and `data.revision`
into the threads persistence owner before rendering or creating state. A
healthy reload starts with empty `save-status` and an unlatch. If GET is empty,
default-thread creation is the first queued save against the returned
revision. Never infer a revision from content.

### Frozen artifact adaptations

`tests/conftest.py` obtains the current revision before cleanup DELETE and
retries 409. Existing direct writers in `tests/test_threads_api.py`,
`tests/test_ui.py`, `tests/test_ui_websearch.py`, and
`tests/test_websearch_api.py` obtain/pass revision. Existing storage assertions
accept the revision envelope. `tests/test_persistence_revisions.py` contains
backend-only oracles and imports no Playwright. Browser-only oracles live in
`tests/test_ui_persistence_conflicts.py` and synchronize through explicit
Promise barriers fired when expected PUTs/title commits are captured — no
sleeps, guessed microtask turns, or immediate asynchronous request counts.

Required DAG: storage.py first; threads.py depends on storage; threads.js
depends on both backend tasks; app.js depends on all three and is final.

v73 restages complete `tests/test_storage_service.py` with two deterministic
failure oracles. Both use monkeypatch/caplog against the locked storage module
surface; neither relies on source line numbers.

## Test-to-file mapping

Backend nodes:

* `tests/test_storage_service.py::test_backup_rotation_failure_preserves_primary_and_is_logged`
  → `src/services/storage.py` (AC-75 + AC-82 correction).
* `tests/test_storage_service.py::test_cleanup_failure_does_not_mask_original_save_error`
  → `src/services/storage.py` (AC-75 correction).

* `tests/test_threads_api.py::test_get_with_no_saved_data_returns_empty`
  → `src/api/threads.py` (AC-136; adapted carried test).
* `tests/test_persistence_revisions.py::test_legacy_raw_primary_and_restored_backup_read_at_revision_zero`
  → `src/services/storage.py` (AC-137).
* `tests/test_persistence_revisions.py::test_accepted_write_migrates_legacy_primary_and_restored_backup`
  → `src/services/storage.py` (AC-138).
* `tests/test_persistence_revisions.py::test_put_without_revision_is_422_and_writes_nothing`
  → `src/api/threads.py` (AC-139).
* `tests/test_persistence_revisions.py::test_delete_without_revision_is_422_and_writes_nothing`
  → `src/api/threads.py` (AC-140).
* `tests/test_persistence_revisions.py::test_each_accepted_put_advances_revision`
  → `src/api/threads.py` (AC-141).
* `tests/test_persistence_revisions.py::test_each_accepted_delete_advances_revision`
  → `src/api/threads.py` (AC-142).
* `tests/test_persistence_revisions.py::test_stale_put_leaves_primary_and_backup_unchanged`
  → `src/api/threads.py` (AC-143; API task depends on storage).
* `tests/test_persistence_revisions.py::test_stale_delete_leaves_primary_and_backup_unchanged`
  → `src/api/threads.py` (AC-144; API task depends on storage).
* `tests/test_persistence_revisions.py::test_two_concurrent_same_revision_puts_have_one_winner`
  → `src/api/threads.py` (AC-145; API task depends on storage).

D-64 browser nodes all map to the final task (`src/static/app.js`), whose
dependencies cover every implementation file:

* `tests/test_ui_persistence_conflicts.py::test_browser_serializes_rapid_mutations_in_revision_order`
  → `src/static/app.js` (AC-146).
* `tests/test_ui_persistence_conflicts.py::test_browser_conflict_warns_and_stops_further_writes`
  → `src/static/app.js` (AC-147).
* `tests/test_ui_persistence_conflicts.py::test_reload_after_conflict_hydrates_and_allows_a_new_save`
  → `src/static/app.js` (AC-148).

All other node ids remain shell-owned regression coverage.
