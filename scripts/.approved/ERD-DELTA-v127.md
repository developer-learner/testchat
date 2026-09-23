# ERD-DELTA v127 — per-thread saving + regression oracles for the 2026-09-23 fixes

Freeze context: standing spec v126 (T9 acceptance-only closeout). Every save
today sends the whole history under one revision, so two tabs conflict on
unrelated chats and saves grow with history. v127 gives each thread its own
revision and saves one chat per request. It also freezes regression oracles
for the three direct fixes of 2026-09-23 (D-132), which landed without tests.

## Design

- Each stored thread may carry an integer `revision` (absent = 0). The
  envelope `revision` stays and still guards the whole-history PUT/DELETE,
  which remain for clear-all and seeding; every per-thread write also bumps
  it by one.
- `save_thread_snapshot(thread, expected_revision)` and
  `delete_thread_snapshot(thread_id, expected_revision)` in
  `src/services/storage.py` compare against the named thread's revision only,
  under the existing process lock, and write through the same temp-file,
  `.bak` and `os.replace` steps. A primary that exists but is not a readable
  threads document raises `SnapshotUnavailableError`; it is never
  overwritten by a per-thread write.
- `PUT /api/v1/threads/{thread_id}` (body `{revision, thread}`) and
  `DELETE /api/v1/threads/{thread_id}` (body `{revision}`) map conflicts to
  the existing 409 shape and an unreadable primary to the existing 503.
  `ThreadSnapshot` gains an optional `revision` so GET returns it; threads
  never saved per thread come back unchanged.
- The browser keeps, per chat, a fingerprint of its last queued content and
  its last accepted revision. `persistThreads()` queues one per-thread PUT
  for each chat whose fingerprint changed and one per-thread DELETE for each
  chat that disappeared. The fingerprint leaves out `model`: the picker sets
  a chat's model in memory on load, and that alone must not save (two tabs
  would conflict before anyone edits). The model rides along with the chat's
  next content change; bare model picks stay in the client store (P2-8).
- `app.js` hands the hydrated chats to the saver right after startup
  hydration, so they start clean.
- The queue, serial drain, conflict latch and exact warning text are carried
  unchanged; only the request shape changes.

## Changed acceptance criteria

- AC-189 (new): PUT with the thread's current revision stores it at n+1.
- AC-190 (new): PUT with a stale revision is a 409, nothing changes.
- AC-191 (new): saves to two different threads are both accepted.
- AC-192 (new): PUT without a revision is a 422, nothing changes.
- AC-193 (new): PUT whose body id differs from the path id is a 422.
- AC-194 (new): DELETE with the current revision removes exactly that thread,
  such that a later GET lists every other thread and not that one.
- AC-195 (new): DELETE with a stale revision is a 409, such that the primary
  and backup bytes are unchanged.
- AC-196 (new): DELETE of a thread that is not stored is a 200, such that the
  primary and backup bytes are unchanged.
- AC-197 (new): an unreadable primary is a 503 and is never overwritten.
- AC-198 (new): concurrent saves of one thread accept exactly one.
- AC-199 (new): one chat per save request, model-only changes ride along.
- AC-200 (new, supersedes AC-146): serial saves chain each chat's accepted
  revision.
- AC-201 (new, supersedes AC-147): a 409 on a per-thread save or delete shows
  the exact warning, such that the page sends no further save or delete.
- AC-202 (new, supersedes AC-156 and AC-157): deleting one chat sends its
  per-thread DELETE and no whole-history save, such that after a reload all
  and only the surviving chats appear.
- AC-203 (new): a failed per-thread save shows `not saved` and the next
  accepted save clears it (AC-75/AC-76 continue for this path).
- AC-204 (new): two tabs editing different chats both persist, no warning.
- AC-205, AC-206, AC-207 (new): regression oracles for the 2026-09-23 direct
  fixes in `src/api/chat.py`, `src/services/llm.py`, `src/api/status.py`.
- AC-148 and AC-158 are carried unchanged; their tests are restaged for the
  per-thread request shape.

## Superseded acceptance criteria

- AC-146 (rapid mutations PUT the whole snapshot in revision order) —
  superseded by AC-200.
- AC-147 (409 on the whole-snapshot PUT latches the page, such that no later
  save or delete is sent) — superseded by AC-201.
- AC-156 (deleting one thread persists the survivor snapshot through the
  revisioned replacement path) — superseded by AC-202.
- AC-157 (per-thread deletion uses PUT with the survivor snapshot, such that
  survivors can never be replaced by an empty snapshot) — superseded by
  AC-202.

## Changed files

- `src/services/storage.py` (UPDATED): per-thread save and delete.
- `src/api/threads.py` (UPDATED): per-thread routes; optional `revision` on
  `ThreadSnapshot`; `ThreadSavePayload`.
- `src/static/app.js` (UPDATED): one line — hand hydrated chats to the saver.
- `src/static/threads.js` (UPDATED): per-chat saving.
- `src/api/chat.py`, `src/services/llm.py`, `src/api/status.py` (no edit —
  acceptance-only): the 2026-09-23 fixes are in place; their new oracles run.
- Tests: `tests/test_thread_saves_api.py`, `tests/test_ui_thread_saves.py`,
  `tests/test_live_fix_regressions.py` (new); `tests/test_ui_persistence_conflicts.py`,
  `tests/test_data_safety_ui.py`, `tests/test_ui.py` (restaged for the
  per-thread request shape; every in-page wait is now bounded at 10 s so a
  wrong build fails fast instead of hanging the suite).

## Coder briefs (verbatim)

### T1 — src/services/storage.py (per-thread save and delete)

Add three private helpers and two public functions to `src/services/storage.py`, placed directly above `def save_versioned_snapshot`.

1. `def _read_threads_for_write(path: str) -> tuple[list[dict], int]:` — if `os.path.exists(path)` is False, return `([], 0)`. Otherwise `data = _read_any(path)`. If `data` is a list, return `(list(data), 0)`. If `data` is a dict whose `"threads"` value is a list, return `(list(data["threads"]), rev)` where `rev` is `data.get("revision")` when it is an int >= 0, else 0. In every other case `raise SnapshotUnavailableError()`.
2. `def _thread_revision(thread: dict) -> int:` — return `thread.get("revision")` when it is an int >= 0, else 0.
3. `def _write_threads_locked(path: str, threads: list[dict], revision: int) -> None:` — make the parent directory exactly as `_save_versioned_snapshot_locked` does, then write `{"revision": revision, "threads": threads}` with the same `tempfile.mkstemp` write, `shutil.copy2` to `f"{path}.bak"` when the primary exists, `os.replace`, and the same temp-file cleanup and re-raise on error.
4. `def save_thread_snapshot(thread: dict, expected_revision: int) -> int:` — inside `with _lock:`, set `path = _data_path()` and `threads, envelope = _read_threads_for_write(path)`. Find the index of the stored thread whose `"id"` equals `thread["id"]`. `current = _thread_revision(threads[index])` when found, else 0. If `current != expected_revision`, `raise SnapshotConflict(current)`. Otherwise build `stored = {**thread, "revision": current + 1}`, replace it at that index (or append it when not found), call `_write_threads_locked(path, threads, envelope + 1)`, and return `current + 1`.
5. `def delete_thread_snapshot(thread_id: int, expected_revision: int) -> bool:` — inside `with _lock:`, read the same way. When no stored thread has `"id" == thread_id`, return False without writing. Otherwise `current = _thread_revision(that thread)`; if it differs from `expected_revision`, `raise SnapshotConflict(current)`; else remove that thread, call `_write_threads_locked(path, threads, envelope + 1)`, and return True.

Self-verify: the existing functions are untouched; `save_thread_snapshot(new_thread, 0)` on an empty store returns 1; `SnapshotUnavailableError` propagates to the caller.

### T2 — src/api/threads.py (per-thread routes)

1. Add `delete_thread_snapshot` and `save_thread_snapshot` to the existing `from src.services.storage import (...)` list.
2. In `class ThreadSnapshot`, add the field `revision: int | None = Field(default=None, ge=0)` after `locked`.
3. Add `class ThreadSavePayload(BaseModel):` with fields `revision: int = Field(ge=0)` and `thread: ThreadSnapshot`.
4. At the end of the file add `@router.put("/api/v1/threads/{thread_id}")` on `def put_thread(thread_id: int, payload: ThreadSavePayload):`. When `payload.thread.id != thread_id`, return `JSONResponse(status_code=422, content={"detail": "thread id mismatch"})`. Build `thread = payload.thread.model_dump(exclude_none=True)` then `thread.pop("revision", None)`, and call `new_revision = save_thread_snapshot(thread, payload.revision)`. On `except SnapshotConflict as exc:` return `JSONResponse(status_code=409, content={"error": "revision_conflict", "current_revision": exc.current_revision})`. On `except SnapshotUnavailableError:` return `JSONResponse({"detail": "snapshot unavailable"}, status_code=503)`. On success return `{"status": "ok", "revision": new_revision}`.
5. Then add `@router.delete("/api/v1/threads/{thread_id}")` on `def delete_thread(thread_id: int, body: ThreadsRevisionPrecondition | None = None):`. When `body is None`, return `JSONResponse(status_code=422, content={"detail": "Missing required field: revision"})`. Call `delete_thread_snapshot(thread_id, body.revision)` with the same 409 and 503 handling, and return `{"status": "ok"}` on success.

Self-verify: `get_threads`, `put_threads` and `delete_threads` are unchanged; a PUT to `/api/v1/threads/1` with `{"revision": 0, "thread": {...id 1...}}` on an empty store returns `{"status": "ok", "revision": 1}`.

### T3 — src/static/app.js (hand hydrated chats to the saver)

In the startup hydration success handler, inside `if (data.threads && data.threads.length > 0) {`, directly after the `for` loop that sets `TC.threadCounter`, add exactly this line:

`if (Threads.markHydrated) Threads.markHydrated(TC.threads);`

Self-verify: one line added, at that position; the rest of the file is byte-identical.

### T4 — src/static/threads.js (save one chat per request)

1. Below `var _conflictLatched = false;` add `var _savedThreads = {};` (chat id -> fingerprint of its last queued content) and `var _threadRevisions = {};` (chat id -> last accepted revision).
2. Inside the `window.Threads` function, after `setHydratedRevision`, add `function _fingerprint(t)` returning `JSON.stringify({ id: t.id, title: t.title, messages: t.messages, locked: !!t.locked })` (no `model`, on purpose); `function _threadPayload(t)` returning `{ id: t.id, title: t.title, messages: t.messages, model: t.model || '', locked: !!t.locked }`; and `function markHydrated(threads)` that sets `_savedThreads[t.id] = _fingerprint(t)` and `_threadRevisions[t.id] = t.revision || 0` for each thread.
3. In `_drainPersistQueue`, make the hydration guard also return when the head type is `'THREAD_PUT'`, and send types `'THREAD_PUT'` and `'THREAD_DELETE'` to `_doThreadMutation(entry)`.
4. Add `function _doThreadMutation(entry)`: `id = entry.payload.id`; body `{ revision: _threadRevisions[id] || 0 }`, plus `thread: entry.payload.thread` for THREAD_PUT; `fetch('/api/v1/threads/' + id, ...)` with method PUT or DELETE and a JSON header. On 409 call `_handleConflict()`. On any other non-ok status or a rejected fetch: set `el('status-save').textContent = 'not saved'`, `delete _savedThreads[id]`, shift the queue, set `_persistRunning = false`, drain. On 200: PUT sets `_threadRevisions[id] = data.revision`, DELETE deletes it; clear `status-save`; shift, set `_persistRunning = false`, drain.
5. Make `persistThreads()` loop over `TC.threads`: when `_fingerprint(t) !== _savedThreads[t.id]`, store the new fingerprint and `_enqueueMutation('THREAD_PUT', { id: t.id, thread: _threadPayload(t) })`. Then, for every key in `_savedThreads` with no chat left in `TC.threads`, delete the key and `_enqueueMutation('THREAD_DELETE', { id: Number(key) })`.
6. In `deleteThread`, replace `_enqueueMutation('PUT', { threads: _captureSnapshot() });` with `persistThreads();`.
7. Add `markHydrated: markHydrated` to the returned object.

Self-verify: renaming one chat queues exactly one `THREAD_PUT` for it.

### T5 — src/api/chat.py (acceptance-only)

No code change. The 2026-09-23 fix (sync `chat` handler) is in place. Preserve the file byte-for-byte and run its mapped tests.

### T6 — src/services/llm.py (acceptance-only)

No code change. The 2026-09-23 fix (skip chunks with no `choices`) is in place. Preserve the file byte-for-byte and run its mapped tests.

### T7 — src/api/status.py (acceptance-only)

No code change. The 2026-09-23 fix (RAM readout by listening port) is in place. Preserve the file byte-for-byte and run its mapped tests.

## Task DAG

Task order: T1 (storage) -> T2 (threads API) -> T3 (app.js) -> T4 (threads.js)

T5, T6 and T7 are acceptance-only and independent. Browser oracles are pinned
to `src/static/threads.js`, the last task, so they run with the full stack.

## Test-to-file mapping

* `tests/test_thread_saves_api.py::test_storage_saves_a_new_thread_at_revision_one`
  -> `src/services/storage.py`
* `tests/test_thread_saves_api.py::test_storage_stale_thread_revision_raises_conflict`
  -> `src/services/storage.py`
* `tests/test_thread_saves_api.py::test_storage_deletes_only_the_named_thread`
  -> `src/services/storage.py`
* `tests/test_thread_saves_api.py::test_storage_refuses_to_save_over_an_unreadable_primary`
  -> `src/services/storage.py`
* `tests/test_thread_saves_api.py::test_put_thread_with_current_revision_is_accepted`
  -> `src/api/threads.py`
* `tests/test_thread_saves_api.py::test_put_thread_treats_a_legacy_thread_as_revision_zero`
  -> `src/api/threads.py`
* `tests/test_thread_saves_api.py::test_put_thread_with_stale_revision_conflicts`
  -> `src/api/threads.py`
* `tests/test_thread_saves_api.py::test_put_thread_that_was_deleted_elsewhere_conflicts`
  -> `src/api/threads.py`
* `tests/test_thread_saves_api.py::test_edits_to_different_threads_from_the_same_state_both_persist`
  -> `src/api/threads.py`
* `tests/test_thread_saves_api.py::test_put_thread_without_revision_is_rejected`
  -> `src/api/threads.py`
* `tests/test_thread_saves_api.py::test_put_thread_with_mismatched_id_is_rejected`
  -> `src/api/threads.py`
* `tests/test_thread_saves_api.py::test_delete_thread_with_current_revision_removes_only_it`
  -> `src/api/threads.py`
* `tests/test_thread_saves_api.py::test_delete_thread_with_stale_revision_conflicts`
  -> `src/api/threads.py`
* `tests/test_thread_saves_api.py::test_delete_thread_already_gone_is_ok_and_changes_nothing`
  -> `src/api/threads.py`
* `tests/test_thread_saves_api.py::test_put_thread_over_unreadable_primary_returns_503`
  -> `src/api/threads.py`
* `tests/test_thread_saves_api.py::test_concurrent_saves_of_one_thread_accept_exactly_one`
  -> `src/api/threads.py`
* `tests/test_ui_thread_saves.py::test_editing_one_chat_saves_only_that_chat`
  -> `src/static/threads.js`
* `tests/test_ui_thread_saves.py::test_two_tabs_editing_different_chats_both_persist`
  -> `src/static/threads.js`
* `tests/test_ui_persistence_conflicts.py::test_browser_serializes_rapid_mutations_in_revision_order`
  -> `src/static/threads.js`
* `tests/test_ui_persistence_conflicts.py::test_browser_conflict_warns_and_stops_further_writes`
  -> `src/static/threads.js`
* `tests/test_ui_persistence_conflicts.py::test_reload_after_conflict_hydrates_and_allows_a_new_save`
  -> `src/static/threads.js`
* `tests/test_data_safety_ui.py::test_delete_one_thread_survives_reload`
  -> `src/static/threads.js`
* `tests/test_data_safety_ui.py::test_hydration_failure_warns_retries_and_recovers_saving`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_save_failure_indicator_shows_then_clears`
  -> `src/static/threads.js`
* `tests/test_live_fix_regressions.py::test_chat_precheck_does_not_stall_other_requests`
  -> `src/api/chat.py`
* `tests/test_live_fix_regressions.py::test_stream_skips_a_chunk_without_choices`
  -> `src/services/llm.py`
* `tests/test_live_fix_regressions.py::test_ram_readout_finds_external_server_by_listening_port`
  -> `src/api/status.py`
