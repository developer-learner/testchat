ERD Delta — testchat M35: composer keyboard behavior — Ctrl+Enter sends, Enter inserts newline (spec v84)

v83 corrects the v82 install rather than changing the milestone:
1. The two AC-153 tests (`test_message_input_ctrl_enter_sends`,
   `test_message_input_cmd_enter_sends`) now select a model before pressing
   the send shortcut. Root cause: the submit handler's no-model guard
   (AC-131) returns "Pick a model" when `model-select` is empty, so the
   shortcut never produced a message bubble — the tests never selected a
   model. They are fixed to mirror the suite's own pattern
   (`select_option("beta-model")` on the locked `model-select` testid).
2. Placement is now frozen DATA, not prose: `contracts.test_mapping` pins
   every M35 node-id to its behavioral owner, and the plan gate places each
   pinned node-id at the task owning that file wherever the EM mapped it.
   The v82 "final task accepts all browser node-ids" placement is retired
   for mapped node-ids; D-64 remains only as the fallback for unpinned
   browser node-ids.
3. The vacuous app.js smoke check is retired: it grepped three pre-existing
   symbols (webToggle/pollStatus/queueRender) that the milestone never
   touched, so T1 gated nothing and accepted with zero evidence. T1 now
   gates the five app.js-pinned tests directly.

## Changed acceptance criteria

v80 introduces AC-152 through AC-155, pinning the composer's keyboard
behavior: plain Enter inserts a newline and never sends; Ctrl+Enter (or
Cmd+Enter on macOS) sends through the send-button path; the empty-input
guard is unchanged; the placeholder states the shortcuts. The prior
behavior — Enter sends, Shift+Enter inserts a newline — was never pinned by
a frozen AC; the one test that exercised Enter-to-send
(test_ui.py:test_no_loaded_model_shows_placeholder_and_send_guides) is
updated to the new shortcut.

Four legacy acceptance criteria (the persistence-mutation and
reload-recovery rules) are reworded, meaning-preserving, to carry the
observable post-condition clauses the S5 lint requires: missing-revision
requests keep returning 422, empty-snapshot writes keep advancing the
revision by one, stale-revision writes keep returning 409, and reload
recovery keeps working. Their pinned behaviors and the tests that pin them
are unchanged.

## Superseded acceptance criteria

None. No frozen AC stated the Enter-to-send behavior; the behavior itself
changes (see Changed acceptance criteria).

## Changed files

### `src/static/app.js`

The message-input keydown handler currently submits the form on plain
Enter and lets Shift+Enter default to a newline. Change it so plain Enter
and Shift+Enter keep the textarea's default newline behavior (never send),
and Ctrl+Enter or Cmd+Enter submits the form through the same
`form.requestSubmit()` path the current handler uses — preserving the
existing empty-input guard (submit handler trims and no-ops on empty) and
the IME `isComposing` guard. No other behavior in the file changes.

### `src/static/index.html`

Update the message-input placeholder text to "Type a message... (Ctrl+Enter
to send, Enter for newline)".

### Spec artifacts (this freeze)

- `contracts.json` v83: adds `test_mapping` (frozen behavioral-ownership
  data for every M35 node-id, machine-validated by check-spec-delta.py at
  freeze time), retires the vacuous app.js smoke check (see preamble).
- `tests/test_ui.py`: the two AC-153 shortcut tests gain the missing
  model-selection setup (see preamble). No other test bytes change.
- Frozen-suite restoration from v80 remains in force (see v82 delta);
  no restoration changes this freeze.

## Test-to-file mapping

Behavioral ownership (which AC each frozen test pins, and against which
file) — now carried as frozen data in `contracts.test_mapping`, with the
plan gate placing every pinned node-id at the task owning its file:

- `test_message_input_plain_enter_inserts_newline_without_sending[chromium]`
  — pins AC-152 against `src/static/app.js`.
- `test_message_input_ctrl_enter_sends[chromium]` (UPDATED: model selected
  before pressing the shortcut) — pins AC-153 against `src/static/app.js`.
- `test_message_input_cmd_enter_sends[chromium]` (UPDATED: model selected
  before pressing the shortcut) — pins AC-153 (macOS modifier) against
  `src/static/app.js`.
- `test_message_input_ctrl_enter_empty_sends_nothing[chromium]` — pins
  AC-154 against `src/static/app.js`.
- `test_message_input_placeholder_states_shortcuts[chromium]` — pins AC-155
  against `src/static/index.html`.
- `test_no_loaded_model_shows_placeholder_and_send_guides[chromium]` — the
  no-model guidance path is now reached via Ctrl+Enter; pins AC-131 + AC-153
  against `src/static/app.js`.

Acceptance placement (gate terms): placement is gate-owned and
data-derived. The plan gate moves each node-id pinned by
`contracts.test_mapping` to the task owning its pinned file, wherever the
EM mapped it; unpinned Playwright-importing node-ids fall back to the
D-64 final-task placement. The EM maps node-ids "where natural" and adds
no depends_on edges for placement.

## Task DAG (TPM-authored; the EM copies it, it does not compose)

- T1 — `src/static/app.js` — depends_on: none. Behavioral owner of
  AC-152, AC-153, AC-154 (and the AC-131 no-model guidance path). Gates the
  five app.js-pinned M35 tests.
- T2 — `src/static/index.html` — depends_on: [T1]. Behavioral owner of
  AC-155. Gates the placeholder test.

Required order: T1 (the keydown handler) before T2 (the placeholder text).

## Coder briefs (verbatim — the EM copies these blocks into plan.json and
changes nothing about them; a brief_wrong verdict therefore routes back to
the TPM as a batched bundle, not a mid-run EM rewrite)

### T1 brief — src/static/app.js

**Implementation constraints (FIRST):** JavaScript in the existing file;
edit via anchored SEARCH/REPLACE blocks (D-59) — never retype unchanged
regions. Change nothing outside the message-input keydown handler and its
immediate surroundings. Do not alter the submit handler's empty-input
guard (trims and no-ops on empty) and keep the `isComposing` IME guard.
No new libraries, no new globals.

**Behavioral specification:** the message-input keydown handler currently
submits the form on plain Enter and lets Shift+Enter keep the textarea's
default newline behavior. Invert it: plain Enter keeps the default newline
(never sends); Shift+Enter keeps the default newline; Ctrl+Enter or
Cmd+Enter submits the form through the same `form.requestSubmit()` path
the current handler uses.

**Acceptance condition:** the frozen tests
`test_message_input_plain_enter_inserts_newline_without_sending`,
`test_message_input_ctrl_enter_sends`,
`test_message_input_cmd_enter_sends`,
`test_message_input_ctrl_enter_empty_sends_nothing`, and
`test_no_loaded_model_shows_placeholder_and_send_guides` (all in
tests/test_ui.py) pass. The rename-input Enter-commit behaviors (AC-114,
`thread-rename-input` / `current-thread-title-input`) are untouched.

### T2 brief — src/static/index.html

**Implementation constraints (FIRST):** HTML in the existing file; anchored
edit of the message-input element's placeholder attribute only; no other
markup changes; no script changes.

**Behavioral specification:** update the message-input element's placeholder
text to "Type a message... (Ctrl+Enter to send, Enter for newline)".
Nothing else changes.

**Acceptance condition:** the frozen test
`test_message_input_placeholder_states_shortcuts` (tests/test_ui.py)
passes.
