ERD — testchat M8: Persistence (erd_version 15)

What changes M7 → M8

Two NEW small backend files, two EDITS to existing files. Cut per D-60:
every task is one concern; new files well under 150 lines; existing files
get few, tightly-related anchored edits (D-59 — first production use).

File inventory (M8 build) — intended DAG order

1. src/services/storage.py — NEW (~60 lines, no dependencies)
   Pure snapshot persistence, stdlib only (json, os, tempfile, logging):
   - SNAPSHOT_PATH from env TESTCHAT_DATA, default "data/threads.json"
     (read the env var AT CALL TIME, not import time — tests repoint it).
   - load_snapshot() -> list[dict]: missing file, unreadable file, or
     invalid JSON all return [] (log a warning for corrupt, not an error).
   - save_snapshot(threads: list[dict]) -> None: ensure parent dir exists;
     write to a temp file in the same directory, then os.replace() onto the
     target (atomic — a crash mid-write can never corrupt the stored file).
2. src/api/threads.py — NEW (~55 lines, depends on storage.py)
   APIRouter, pydantic models ThreadSnapshot {id: int, title: str,
   messages: list[{role, content}], model: str = "", locked: bool = False}
   and ThreadsPayload {threads: list[ThreadSnapshot]}.
   - GET  /api/v1/threads    -> {"threads": load_snapshot()} (200 always)
   - PUT  /api/v1/threads    body ThreadsPayload -> save_snapshot(
                             payload as plain dicts) -> {"status": "ok"}
                             (pydantic gives 422 on malformed input)
   - DELETE /api/v1/threads  -> save_snapshot([]) -> {"status": "ok"}
3. src/main.py — EDIT (one concern: mount the router)
   Add a third defensive try/except import block, identical in shape to
   the chat/models ones, including src.api.threads' router.
4. src/static/app.js — EDIT (one concern: persistence wiring; LAST,
   depends on all above). Four small anchored edits:
   a. persistThreads() helper: fetch PUT /api/v1/threads with
      JSON.stringify({threads: threads.map(t => ({id: t.id, title: t.title,
      messages: t.messages, model: t.model || '', locked: !!t.locked}))}),
      fire-and-forget (.catch swallowed — persistence must never break
      chat).
   b. hydrate on startup: replace the bare `createThread();` bootstrap
      call with a fetch of GET /api/v1/threads: on a non-empty threads
      array, rebuild state (threads = data.threads with messages/model/
      locked; threadCounter = max id; activeThreadId = first thread's id;
      renderThreadMessages + restoreThreadModelState + renderSidebar);
      on empty array OR any fetch error, fall back to createThread().
   c. call persistThreads() in the 'done' event handler, immediately after
      the two messages are pushed.
   d. call persistThreads() at the end of createThread().

Data models

ThreadSnapshot / ThreadsPayload as above. The frontend Thread object is
unchanged; the snapshot is its serializable subset (no DOM references).
Assistant message content is already think-free (AC-30) — snapshots
inherit that.

Configuration

TESTCHAT_DATA (env): snapshot file path. Default data/threads.json
relative to the process working directory. The UI-test fixture sets it to
a per-session temp path.

Constraints

All prior constraints carry forward. New:
C-19: storage is stdlib-only (json/os/tempfile/logging) — no new
dependencies, no database engine (PRD A14).
C-20: persistence failures are silent to the user (logged backend-side);
chat must work fully even if the disk write fails.
C-21: AC-25's "refresh clears" behavior is retired; no code or test may
reintroduce it.

Oracle Mapping (AC → test node) — guidance for the plan

Backend node-ids map to the task owning their subject:
- tests/test_storage_service.py::* → the storage.py task (T1).
- tests/test_threads_api.py::*     → the threads.py task (T2).
- The validator will attribute every node-id whose test imports src.main
  (test_chat_api.py, test_chat_model_routing.py, test_models_api.py,
  test_page.py, and test_threads_api.py's app-level tests) to this delta —
  map ALL of those to the src/main.py task (T3): the router mount is
  additive, they must pass immediately after it.
- ALL EIGHT UI node-ids (tests/test_ui.py::*, including the new
  test_threads_survive_reload) → the FINAL app.js task (T4), which
  depends_on T1..T3. Mapping any UI node-id earlier guarantees a false
  strike.
- test_llm_service.py / test_models_service.py stay unmapped (shell-owned
  carry-forward, D-57).

Milestone Justification

Single milestone: one user promise (durability), four one-concern tasks,
each inside the D-60 coder profile. The M9 polish sweep is deliberately
separate.

Test dependencies

No new dependencies (stdlib storage; existing pytest/playwright stack).
tests/conftest.py changes in this freeze: the app fixture exports
TESTCHAT_DATA to a session temp path, and an autouse fixture clears the
snapshot (DELETE /api/v1/threads) before each UI test so tests stay
independent now that state persists across page loads.
