ERD Delta — testchat M35: composer keyboard behavior — Ctrl+Enter sends, Enter inserts newline (spec v80)

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

## Test-to-file mapping

- `test_message_input_plain_enter_inserts_newline_without_sending` — pins
  AC-152 against `src/static/app.js`.
- `test_message_input_ctrl_enter_sends` — pins AC-153 against
  `src/static/app.js`.
- `test_message_input_cmd_enter_sends` — pins AC-153 (macOS modifier)
  against `src/static/app.js`.
- `test_message_input_ctrl_enter_empty_sends_nothing` — pins AC-154 against
  `src/static/app.js`.
- `test_message_input_placeholder_states_shortcuts` — pins AC-155 against
  `src/static/index.html`.
- `test_no_loaded_model_shows_placeholder_and_send_guides` (UPDATED) — the
  no-model guidance path is now reached via Ctrl+Enter; pins AC-131 + AC-153
  against `src/static/app.js`.

Required DAG: `src/static/app.js` first (the keydown handler), then
`src/static/index.html` (the placeholder text).
