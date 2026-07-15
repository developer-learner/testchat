PRD — testchat M23: Honest Saves (maintenance milestone)

Milestone

testchat is feature-complete; M23 is the maintenance pass. An external
audit (2026-07-14) found one real design flaw: when the app saves your
threads, a failure is swallowed silently — a failed save is
indistinguishable from a successful one, so a conversation can be lost
without anyone knowing. M23 makes save failures visible, tightens the one
loosely-validated API, and trues up the spec's file inventory to the
post-split frontend reality (app.js/markdown.js/rain.js/style.css exist
but were never declared).

Acceptance Criteria

- AC-75: WHEN a thread-persist request fails (network error or non-2xx
  response), the status strip SHALL display "not saved" in the
  save-status element.
- AC-76: WHEN a subsequent thread-persist succeeds, the save-status
  element SHALL return to empty.
- AC-77: WHEN a PUT /api/v1/threads payload contains a message role other
  than "user" or "assistant", the API SHALL reject it with 422 and
  persist nothing.
- All prior ACs unchanged.

Maintenance riders (no app-behavior ACs; land with this freeze):

- Frozen-suite lint debt cleared: 7 unused imports removed from
  test_chat_api.py / test_chat_model_routing.py / test_llm_service.py
  (the D-67 gate now rejects new debt at the door).
- Flake hardening from the 2026-07-15 CI record: the SLOWPING stub's
  pre-answer hold rises 1.2s -> 3.0s (widens the placeholder observation
  window), and the persistence-cleanup fixture requires two consecutive
  empty snapshot reads before releasing a test (kills the late-PUT ghost
  thread race).
- Inventory truth: contracts.files now declares the whole frontend;
  app.js / markdown.js / rain.js / style.css enter as no_edit_files
  (D-65 — the coder never sees them, acceptance still runs).

Out of Scope: retrying failed saves automatically (the next user action
re-persists anyway); multi-tab conflict detection (single-user app;
last-writer-wins stays accepted); storage.py justification comments
(rides whichever future milestone next touches that file).

CEO Demo Script

1. Open the app, send a message — status strip shows nothing unusual.
2. Kill the backend (Ctrl-C the uvicorn process), send another message —
   "not saved" appears in the status strip.
3. Restart the backend, send again — the indicator clears.
