ERD — testchat M7: Browser Oracle Retrofit + Chat Hygiene Fixes (erd_version 10)

What changes M6 → M7

Modified: src/static/index.html — the only file. Three changes:
1. Locked testids: every contracts.ui element carries its data-testid.
2. History hygiene: assistant content is stripped of <think>...</think>
   before being pushed to the thread's messages array (display keeps the
   full text in the live bubble; stored history is clean — AC-30).
3. Selection stability: fetchModels() records the current selection before
   rebuilding the dropdown options and restores it afterwards when the id
   is still present (AC-31).

New frozen test files: tests/conftest.py (UI fixtures: capture-shaped LLM
mock + app server) and tests/test_ui.py (Playwright suite, D-58). These are
TPM artifacts, not inventory files — the coder never touches tests/.

No backend files change. No new routes, schemas, or SSE events.

File inventory (M7 build)

src/static/index.html — modified

Data models

Thread (frontend-only, unchanged from M6), with one semantic tightening:
messages[].content for role 'assistant' is ALWAYS think-free (AC-30). The
full streamed text (including think markup) exists only transiently in the
live reply bubble's render state.

Frontend architecture (implementation guidance, not contract)

- data-testid placement: thread-item on each sidebar entry; msg-user /
  msg-assistant on each chat bubble; think-content on each span wrapping
  thinking text inside a reply bubble; the rest are 1:1 with existing
  elements (new-thread-btn, message-input, send-btn, think-toggle,
  model-select, unload-nemotron).
- Think sources are unified at render time: 'think' SSE events wrap their
  content in <think>...</think> before appending to the reply text (as the
  M6 hotfix does); inline <think> arriving via 'token' events (captured
  reality — see external:lmstudio-chat-stream) is already in that form. The
  renderer turns <think> spans into hidden/visible think-content elements.
- strip helper: one function removing <think>...</think> (including
  unterminated trailing <think>... at stream end) used exactly once — when
  committing the reply to thread.messages on 'done'.
- fetchModels(): capture modelSelect.value before innerHTML rebuild;
  after appending options, restore it if an option with that value exists;
  also update the active thread's stored model to the restored value.
- The M6 per-thread lock/save/restore mechanism (saveThreadModelState /
  restoreThreadModelState / per-thread locked flag) is behavior to preserve,
  not rewrite.

Configuration

No new environment variables for the app. UI-test fixtures use fixed
loopback ports (stub LLM 8971, app under test 8972) and set LLM_ENDPOINT on
the app subprocess — sandbox-safe under --network none (loopback only).

Constraints

All M3–M6 constraints carry forward. New:
C-14: UI tests locate elements ONLY via contracts.ui testids (D-58,
enforced by check-test-surface.py at freeze).
C-15: No sleeps or timeout-tuned waits in UI tests (D-58 determinism gate);
Playwright auto-waiting only. Zero retries — a flaky UI test is a spec
defect.
C-16: The UI-test LLM mock serves the captured shapes from
scripts/.approved/captures/ (D-56); content is synthetic, shape is real.

Oracle Mapping (AC → test node)

AC-27 → tests/test_ui.py::test_think_toggle_reveals_and_hides_thinking
AC-28 → tests/test_ui.py::test_model_lock_is_per_thread
AC-29 → tests/test_ui.py::test_thread_switch_restores_history
AC-30 → tests/test_ui.py::test_history_sent_to_backend_has_no_think_markup
AC-31 → tests/test_ui.py::test_model_selection_survives_models_refresh
AC-32 → tests/test_ui.py::test_new_chat_creates_unlocked_empty_thread
AC-33 → tests/test_ui.py::test_thread_title_set_from_first_message
AC-24/25/26 → manual-only (PRD waivers)

The existing 60-test backend suite carries forward unchanged as the
regression bucket (computed by the shell, D-57).

Milestone Justification

Single milestone: the retrofit tests and the two fixes are one coherent
deliverable — the fixes are exactly the defects the retrofit oracle must
prove it can see. Proof criterion (D-58 acceptance): the retrofit tests
fail against the M6 [success] tree (9bfc21a + testids) and pass after the
hotfix (590e205 + testids); the fix tests fail against current HEAD until
the M7 build lands.

Test dependencies

New: playwright, pytest-playwright (chromium provided by the sandbox image,
D-58). Existing: pytest, fastapi.testclient, unittest.mock, httpx,
pytest-httpserver, werkzeug.
