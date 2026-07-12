ERD — testchat M10: Ratify the Sprint (erd_version 20)

What changes v19 → v20

No behavior changes. Two edit-mode tasks add data-testid attributes so the
new frozen browser tests can reach controls that already exist and work
(D-58: tests locate only via locked testids). Everything else in this
freeze is spec artifacts: contracts (3 new routes, 6 new entry points, 9
new testids), AC-44..AC-52, six new UI tests, two new backend test files,
and fixture upkeep in tests/conftest.py.

File inventory (M10 build) — DAG order

1. src/static/index.html — modified (static testids)
   Add data-testid, values exactly: "system-prompt-input" on the
   #system-prompt-input textarea; "settings-save" on #settings-save;
   "settings-cancel" on #settings-cancel; "status-strip" on the
   #status-strip div. The gear (#settings-toggle) and theme
   (#theme-toggle) buttons ALREADY carry their testids — leave them.
   Change nothing else.
2. src/static/app.js — modified (dynamic testids; LAST, depends on 1)
   Three one-line setAttribute additions where renderSidebar creates the
   per-thread controls and where startRename creates the inline input:
   - renBtn.setAttribute('data-testid', 'thread-rename-btn');
   - delBtn.setAttribute('data-testid', 'thread-delete-btn');
   - inp.setAttribute('data-testid', 'thread-rename-input');
   Change nothing else — no behavior edits of any kind (C-22).

Constraints

All prior constraints carry forward. New:
C-22: this milestone may not alter any behavior — testid attributes only.
A task whose diff touches logic is a task failure even if tests stay
green.
C-23: ratifying tests pin current behavior verbatim (PRD A17); where a
current behavior is quirky, the PRD waives rather than the test bending.

Contract ids per task (the validator rejects invented ids):
- src/static/index.html task: contracts = [] (frontend file — never
  invent module-style ids).
- src/static/app.js task: contracts = [] — same rule.

Oracle Mapping (AC → test node) — guidance for the plan

- ALL browser node-ids (tests/test_ui.py::*, now 14 of them) → the FINAL
  task (src/static/app.js), which must depends_on the index.html task.
  Mapping any UI node-id earlier guarantees a false strike (the modal
  testids arrive in task 1, the sidebar testids in task 2).
- The index.html task carries NO mapped tests — its acceptance is its
  contracts.smoke_checks entry (grep for the four new static testids).
- The new backend node-ids (tests/test_settings_api.py::*,
  tests/test_status_api.py::*) exercise no inventory file — do NOT map
  them; the shell runs them in the final full-suite acceptance (D-57).

AC-44 → tests/test_ui.py::test_markdown_renders_readably
AC-45 → tests/test_ui.py::test_theme_switch_persists_across_reload
AC-46 → tests/test_ui.py::test_thread_rename_via_sidebar_control
AC-47 → tests/test_ui.py::test_thread_delete_removes_thread
AC-48 → tests/test_ui.py::test_stop_button_keeps_partial_reply
AC-49 → tests/test_ui.py::test_saved_system_prompt_reaches_requests
AC-50 → tests/test_settings_api.py (roundtrip / default / corrupt-file)
AC-51 → tests/test_settings_api.py::test_env_var_precedence*
AC-52 → tests/test_status_api.py::test_status_returns_json_object

Test-fixture notes (tests/conftest.py changes in this freeze)

- The app fixture exports TESTCHAT_SETTINGS to a session temp path
  (settings isolation, like TESTCHAT_DATA).
- The autouse _fresh_snapshot fixture also resets the saved system prompt
  (PUT empty) before app-facing tests — settings persist across page
  loads now, tests must stay independent.
- The stub LLM gains: (a) a markdown tail on the standard reply so AC-44
  is assertable ("**bold move**", "`mono bit`"); existing assertions on
  "Hello there" are unaffected; (b) a "slow-model" entry whose stream
  emits ~20 spaced chunks over ~3s (sleeps live in conftest, permitted —
  the determinism gate scopes to playwright-importing files) so AC-48 can
  deterministically click Stop mid-stream.

Milestone Justification

One milestone, two trivial edit-mode tasks, everything else frozen
artifacts. The debt this clears: six shipped features currently have zero
mechanical defense; every future build gambles with them until this
lands.

Test dependencies

No new dependencies.
