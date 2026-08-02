ERD Delta — testchat M33 conflict-safe history persistence (erd_version 72)

## Changed acceptance criteria

AC-136 through AC-148 are added exactly as written in the complete replacement
`PRD.md`. AC-35 and AC-37 are constrained by mandatory revision preconditions.
AC-75 and AC-76 continue to govern ordinary save failures. AC-78, AC-79,
AC-80, AC-81, and AC-82 remain unchanged while their storage/API artifacts
adopt the revision envelope. Every other live v71 criterion remains in force,
including AC-111..AC-135.

## Superseded acceptance criteria

M8 flagged assumption A15, "Concurrent tabs are last-write-wins," is formally
superseded. No numbered acceptance criterion is retired. Standing prose that
describes fire-and-forget unordered replacement is superseded only to the
extent AC-136..AC-148 require revisioned, ordered persistence.

## Changed files

### `src/services/storage.py`

Keep `load_snapshot()` as the compatibility view returning only the thread
list and keep `save_snapshot()` usable by frozen callers. Add locked entry
points `load_versioned_snapshot() -> tuple[list[dict], int]` and
`save_versioned_snapshot(threads, expected_revision) -> int`, plus
`SnapshotConflict.current_revision`.

The current on-disk form is one JSON object:

```
{"revision": <non-negative integer>, "threads": [<ThreadSnapshot>...]}
```

A missing primary reads as empty at revision 0. A legacy raw-list primary
reads losslessly at revision 0, including when a human restored a raw-list
`.bak` to the configured primary path. The next accepted write stores the
revision-1 envelope and rotates the legacy primary bytes to `.bak`.
`load_snapshot()` returns only the list from either form. Do not use a content
hash as a generation because equal content may recur (ABA).

Use one module-level process-local lock for the entire read-current / compare /
backup-rotate / temp-write / atomic-replace operation. On mismatch, raise
`SnapshotConflict` before any directory, temp, backup, or primary write. On a
match, always write generation `expected + 1`, including equal PUT and
empty-to-empty DELETE. Preserve same-directory temp replacement, quarantine,
cleanup, and exactly one `.bak` generation. The compatibility `save_snapshot`
must acquire the same lock and advance from the current generation; API code
must not use it.

**D-80 remediation is part of this storage task.** Replace the reported
temp-cleanup `except OSError: pass` at `src/services/storage.py:79` with an
observable warning that includes the temp path and cleanup exception, then
continue to the existing re-raise of the original save failure. The warning
must not mask the original exception; propagation preserves AC-75's user-
visible `not saved` behavior.

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

## Test-to-file mapping

Backend nodes:

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
