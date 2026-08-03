ERD Delta — testchat M33 conflict-safe history persistence, v76 oracle correction (erd_version 76)

Version 76 changes no product requirement or task guidance. It regenerates
the frozen node-id inventory after v75 accidentally collected archived
staging tests and treated byte-identical returned tests as changed. All v74
implementation corrections below remain normative for the pending feature.

## Changed acceptance criteria

v74 adds no numbered acceptance criterion: AC-136 through AC-148 remain
exactly as frozen in v72/v73. This correction answers the T1 caps-exhausted
escalation (spec v73) by making three storage-module behaviors normative
that the v73 prose stated but the built module violated. AC-35 and AC-37
remain constrained by mandatory revision preconditions. AC-75, AC-76,
AC-78, AC-79, AC-80, AC-81, and AC-82 remain unchanged. Every other live
v71 criterion remains in force, including AC-111..AC-135.

## Superseded acceptance criteria

None beyond v73's standing supersessions (M8 assumption A15).

## Changed files

### `src/services/storage.py`

Public surface: keep `load_snapshot()` (list-only compatibility),
`save_snapshot()`, and `quarantine_files()`. Keep
`load_versioned_snapshot() -> tuple[list[dict], int]`,
`save_versioned_snapshot(threads, expected_revision) -> int`, and
`SnapshotConflict.current_revision`.

**v74 corrections — each one names a defect the v73 T1 build shipped and the
frozen oracle rejected. These are normative; the current file on disk is
close and needs exactly these repairs, not a rewrite:**

1. **`save_snapshot` SHALL read the current persisted generation under the
   lock and pass THAT as `expected_revision` to the private helper. It SHALL
   NOT pass a constant.** The v73 build passed `0` unconditionally, so every
   second compatibility save raised `SnapshotConflict` — observed as
   `src.services.storage.SnapshotConflict: revision conflict` across the
   backup-rotation, atomic-overwrite, and bak-rotation oracles. Sequence:
   acquire the module lock once; read the current generation (missing or
   unreadable primary reads as generation 0, a legacy raw list reads as
   generation 0); call `_save_versioned_snapshot_locked(threads, current)`;
   discard the returned revision; return `None` compatibly.

2. **The load path SHALL accept a top-level JSON *list* as the legacy
   primary shape: that list IS the threads, at revision 0.** The v73 build's
   raw reader returned `None` for any non-dict JSON document, so legacy
   primaries (and a `.bak` a human restored as primary) read as `([], 0)` —
   silent total data loss, rejected by AC-137/AC-138 oracles. A top-level
   dict carrying an integer `revision >= 0` and a `threads` list is the
   envelope shape; a top-level list is the legacy shape; anything else
   unreadable follows correction 3. The same generation-reading rule applies
   inside the save path's compare step: a legacy-list primary compares as
   generation 0, and its accepted successor write stores
   `{"revision": expected + 1, "threads": [...]}` while backup rotation
   (`shutil.copy2` of the primary before replacement) preserves the raw
   legacy bytes in `.bak` unchanged.

3. **WHEN the primary exists but does not parse as JSON, the load path SHALL
   quarantine it — move the file aside by rename to
   `<primary-name>.corrupt-<stamp>` in the same directory, preserving its
   bytes exactly — then return `([], 0)`.** The v73 build dropped M24
   quarantine entirely (nothing ever created `.corrupt-*` files), regressing
   AC-78/AC-80: `quarantine_files()` scans for that prefix and the threads
   GET's `quarantined` flag reads it. After quarantine the primary no longer
   exists, so the next save writes revision 1 fresh. Quarantined files are
   never deleted, never overwritten by later saves, and never auto-restored.

4. **Load SHALL NOT automatically fall back to reading `.bak`.** Automatic
   restore from `.bak` is explicitly out of scope (M33 out-of-scope list);
   the v73 build invented a `.bak` recovery path on load. The only supported
   restore is a human moving the backup over the primary, which then reads
   under rule 2. Remove the fallback.

Everything else stands as frozen in v73: one module-level non-reentrant
lock covering read-current / compare / backup / temp-write / atomic-replace /
revision-advance; mismatch raises `SnapshotConflict` before any directory,
temp, backup, or primary write; match always writes `expected + 1`
(including equal PUT and empty DELETE) by same-directory temp replacement;
exactly one `.bak`, rotated by `shutil.copy2(primary, bak)` before
`os.replace(temp, primary)`; parent directory created when missing.

Failure handlers remain exactly as v73 froze them, and the current build
already passes the cleanup oracle — do not regress it:

1. If `shutil.copy2(primary, bak)` raises `OSError`, warn with primary path,
   backup path, and exception text, then re-raise that same exception
   object. Outer failure handling removes the temp file and propagates the
   original error; primary bytes and revision stay fixed; no `.bak` appears.
2. If temp unlink then fails while handling any save error, warn with the
   exact temp path and the cleanup exception, but re-raise the ORIGINAL
   error, never cleanup's.

### `src/api/threads.py`

Unchanged from v73's delta prescription:

Extend `ThreadsPayload` with required `revision: int >= 0`. Add a DELETE body
model containing required `revision: int >= 0`. GET performs one revisioned
load and returns `{"threads": [...], "revision": n, "quarantined": bool}`.
PUT calls `save_versioned_snapshot(payload.threads, payload.revision)`; DELETE
calls it with `[]`. Both return `{"status":"ok", "revision": n+1}`.

Map `SnapshotConflict` to HTTP 409 with the exact top-level JSON body
`{"error":"revision_conflict", "current_revision": n}`; do not wrap it in
FastAPI's `detail`. Validation failures remain 422 and write nothing.

### `src/static/threads.js`

Unchanged from v73's delta prescription:

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

Unchanged from v73's delta prescription:

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

v74 restages `tests/test_storage_service.py` and
`tests/test_persistence_revisions.py` byte-identical: the oracles were
correct; the correction is entirely on the implementation-guidance side.

## Plan authoring — task object shape

The plan validator (`scripts/validate-plan.py`) rejects any task whose keys
are not EXACTLY the six required: `id`, `file`, `depends_on`, `brief`,
`contracts`, `tests`. No other keys are permitted at the task level, and no
required key may be omitted or renamed. In particular the field naming the
frozen pytest node-ids the task must pass is `tests` — NOT `test_nodes`,
`test_ids`, `nodeids`, `acceptance`, `regression`, or any synonym. The task
object shape is exactly:

    {
      "id": "T1",
      "file": "src/services/storage.py",
      "depends_on": [],
      "brief": "one concern, ≤2500 chars, describes the change to `file`",
      "contracts": ["route:threads_get", "schema:threads_payload"],
      "tests": ["tests/test_storage_service.py::test_backup_rotation_failure_preserves_primary_and_is_logged",
                "tests/test_persistence_revisions.py::test_each_accepted_put_advances_revision"]
    }

Field rules:

* `id` — task identifier, string, unique within the plan (e.g. `T1`, `T2`).
* `file` — the one repo-relative path this task edits. Every task edits
  exactly one file; multi-file work is decomposed into multiple tasks.
* `depends_on` — list of task ids from THIS subtree that must complete
  before this task runs. Use `[]` for the root; do not reference tasks in
  other plans.
* `brief` — implementation guidance, one concern per task, ≤2500 characters.
  Empty briefs and negative-only wording are rejected.
* `contracts` — list of contract ids from `scripts/.approved/contracts.json`
  (`entry_points` / `routes` / `schemas` / `errors`) this task must honor.
  Use `[]` when the file has no directly-associated contract entry.
* `tests` — list of frozen pytest node-ids drawn from
  `scripts/.approved/test-nodeids`, each of the form
  `tests/<file>.py::test_name` (parametrized ids include their `[…]`
  suffix). This is the acceptance oracle for the task; every node-id
  named in the outer envelope's `map_nodeids` for the subtree must be
  assigned to exactly one task.

The outer plan envelope carries `erd_version` and `version`; individual
tasks must not carry `erd_version`, `status`, or any additional key.

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
