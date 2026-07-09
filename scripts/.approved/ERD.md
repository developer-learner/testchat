ERD — testchat M7: Browser Oracle Retrofit + Chat Hygiene Fixes (erd_version 13)

What changes v10 → v11 (why this delta exists)

The v10 build failed exactly as the model bench predicted: one task asking
the coder to regenerate a 638-line index.html with three concerns deleted
working features (commit efdda29, all 7 UI tests red — the oracle caught
it). v11 changes the DECOMPOSITION, not the behavior: the frontend splits
into three files so every coder task is small and single-concern. The
frozen test suite is UNCHANGED from v10 — tests observe only the browser
through locked testids, so this refactor is invisible to them.

The repo has been mechanically pre-split (a byte-verified, behavior-
preserving extraction committed before this milestone runs), so every task
below EDITS an existing file — no file is written from scratch.

File inventory (M7 build) — intended DAG order

1. src/static/style.css — modified (T-first, no dependencies)
   All CSS, extracted verbatim from the old <style> block. M7 change:
   NONE beyond what already exists. The task is a no-op guard: keep the
   .think-content display rules (hidden by default, visible under
   .show-thinking) intact.
2. src/static/app.js — modified (depends on style.css)
   All application JS, extracted from the old <script> block (the IIFE).
   M7 changes, exactly three, all small:
   a. data-testid attributes on DYNAMICALLY created elements:
      thread-item (sidebar entries), msg-user / msg-assistant (chat
      bubbles, including the live streaming reply bubble and re-rendered
      history bubbles), think-content (the spans renderThink emits).
   b. History hygiene (AC-30): one helper that strips <think>...</think>
      spans (including an unterminated trailing <think>...) — applied in
      exactly one place: when pushing the assistant reply into
      thread.messages on the 'done' event. The live bubble keeps showing
      the full text; only STORED history is stripped.
   c. Selection stability (AC-31): fetchModels() records
      modelSelect.value before rebuilding options and re-selects it after
      if an option with that value still exists; also update the active
      thread's stored model to the restored value.
3. src/main.py — modified (independent; can run any order)
   Add a StaticFiles mount so the browser can load the split assets:
   from fastapi.staticfiles import StaticFiles;
   app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")
   Everything else in the file stays exactly as it is.
4. src/static/index.html — modified (LAST; depends on all above)
   The static shell: head, top bar, sidebar, chat container, form. M7
   changes: data-testid attributes on the STATIC elements
   (new-thread-btn, message-input, send-btn, think-toggle, model-select,
   unload-nemotron); it links the split assets via
   <link rel="stylesheet" href="/static/style.css"> and
   <script src="/static/app.js"></script> (already present after the
   pre-split — preserve them).

Data models

Thread (frontend-only, unchanged from v10): messages[].content for role
'assistant' is ALWAYS think-free (AC-30). Full streamed text exists only
in the live reply bubble's render state.

Constraints

All v10 constraints carry forward (C-14 testid-only UI tests, C-15 no
sleeps, C-16 mocks from captures). New:
C-17: main.py serves /static/* via StaticFiles; index.html references
assets ONLY by those absolute /static/ paths.
C-18: the split is a refactor — no behavior may change except the three
M7 changes listed under app.js and the testid attributes. Deleting or
rewriting working logic is a task failure even if unrelated tests stay
green.

Oracle Mapping (AC → test node) — guidance for the plan

The 7 UI node-ids (tests/test_ui.py::*) exercise the WHOLE stack — they
need the mount, the shell, the JS, and the CSS all in place. Map ALL
SEVEN to the FINAL task in the DAG (src/static/index.html), which must
depend_on every other task. Mapping any UI node-id to an earlier task
guarantees a false strike: the app is not whole until the last task.

Because src/main.py is in this delta's inventory, every backend node-id
whose test imports src.main is attributed to this delta by the validator
(D-57) and MUST be mapped — map ALL node-ids from test_chat_api.py,
test_chat_model_routing.py, test_models_api.py and test_page.py to the
src/main.py task: the mount is purely additive, so they must pass
immediately after it. Node-ids the validator does not attribute
(test_llm_service.py, test_models_service.py) stay unmapped — the shell
carries them to the final full-suite run. The style.css and app.js tasks
carry NO mapped tests — their per-task acceptance is their
contracts.smoke_checks entry (v12).

AC-27 .. AC-33 → the seven tests/test_ui.py node-ids (see v10 mapping,
unchanged). AC-24/25/26 → manual-only (PRD waivers).

Milestone Justification

Same milestone as v10 — the delta only right-sizes the tasks after the
v10 halt. Sizing per D-46: four atomic tasks, each well inside the
coder-class comfort zone measured in the bench (single file, one concern,
brief under 1000 chars).

Test dependencies

Unchanged from v10: playwright, pytest-playwright (chromium in the
sandbox image), pytest, fastapi.testclient, httpx.
