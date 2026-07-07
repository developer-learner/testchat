ERD — testchat M6: Multichat In-Memory Threads (erd_version 9)

What changes M5 → M6

Modified: src/static/index.html — the only file. Layout changes from a
single full-width chat panel to a sidebar + panel split. All JavaScript state
that was flat (conversation, messageSent, replyText) becomes per-thread,
stored in an in-memory array of thread objects. A thread-switching mechanism
swaps DOM content and restores per-thread model/lock state.

No backend files are touched. No new files are created.

File inventory (M6 build)

src/static/index.html — modified

Data models

Thread (frontend-only, JavaScript object, not a Pydantic model):
{ id: string (unique, e.g. crypto.randomUUID() or counter),
  title: string (default "New Chat", updated to first message truncated ~40 chars),
  messages: array of {role, content} (same shape as history sent to API),
  bubbles: DOM nodes or HTML string for the chat container,
  selectedModel: string (model-select value),
  modelLocked: boolean (true after first send),
  activeStream: object | null (in-flight SSE reader state, if any) }

No backend data models change. ChatRequest, HistoryEntry, ModelInfo,
SSEToken, SSEDone, SSEError, NemotronLoadResponse, NemotronUnloadResponse —
all unchanged.

Frontend architecture (implementation guidance, not contract)

The existing IIFE wraps all state. M6 refactors the flat variables into a
threads array and an activeThreadId. The key operations:

createThread(): push a new Thread object, switch to it.
switchThread(id): save current thread's state (selectedModel, modelLocked,
  bubbles innerHTML), restore target thread's state into the DOM.
updateTitle(thread, firstMessage): truncate to ~40 chars, update sidebar.

The submit handler changes from writing to flat `conversation`/`replyText` to
writing to `threads[activeThreadId]`. The SSE read loop captures the thread
reference at send time so switching threads mid-stream doesn't corrupt state.

Nemotron load/unload and fetchModels() remain global — they update the
model-select options regardless of active thread.

CSS: body gains a flex-row wrapper. Sidebar is ~250px fixed-width, chat panel
takes remaining space. Sidebar entries have an active highlight. Minimal
styling consistent with existing design language.

Configuration

No new environment variables. No backend configuration changes.

Constraints

All M3–M5 constraints carry forward. New:
C-12: Thread state is purely in-memory. No localStorage, no sessionStorage,
no IndexedDB, no backend persistence. Refresh = full reset.
C-13: No backend routes are added or modified. M6 is entirely
src/static/index.html.

Oracle Mapping (AC → test node)

AC-18 through AC-26 are frontend-only (CEO Demo Script verified). No pytest
tests are added for M6 — the backend is unchanged and the existing frozen
suite continues to pass as-is.

Since M6 modifies only src/static/index.html and adds no backend behavior,
the existing test_page.py (which tests GET / returns 200 with text/html)
remains the only backend oracle for the static file.

Milestone Justification

Single milestone — all ACs are aspects of one feature (multi-thread UI) with
no separable backend deliverable.

Test dependencies

No new test dependencies. Existing: pytest, fastapi.testclient, unittest.mock,
httpx, pytest-httpserver, werkzeug.
