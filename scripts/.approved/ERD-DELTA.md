# ERD-DELTA — spec v102 composer keyboard send removal (consolidation)

Consolidation freeze: this milestone pins the composer keyboard removal that
shipped as a direct fix (2026-08-13, D-132 routing — the Ctrl+Enter / Cmd+Enter
send shortcut is gone; the Send button is the only send path). No app
behavior is introduced by this delta — the fix is on the tree; this freeze
adds the acceptance criteria and the UI oracle that prove the shortcut cannot
regress, clearing the regression-test gap left when the direct fix crossed
the lane.

## Changed acceptance criteria

* **AC-130 (amended):** the no-model clause now also requires the Send
  control itself to be disabled ("...and SHALL disable the Send control,
  such that no message can be dispatched without a loaded model") — the
  disabled button replaces the AC-131 guidance bubble as the no-model
  affordance.

* **AC-168 (NEW — replaces AC-153/AC-154):** THE Send button SHALL be the
  ONLY path that dispatches a message; no keyboard combination (Ctrl+Enter,
  Cmd+Enter, Shift+Enter, plain Enter, or any other key event) SHALL send,
  such that pressing any key in the message input never produces a message
  bubble or a chat request.

* **AC-169 (NEW — replaces AC-155):** THE message input's placeholder SHALL
  state only that Enter inserts a newline ("Type a message... (Enter for
  newline)") and SHALL NOT advertise any keyboard send shortcut.

## Superseded acceptance criteria

* **AC-131:** the "Pick a model" guidance bubble is retired; the disabled
  Send control (AC-130 amendment) is the no-model affordance. The old test
  (test_no_loaded_model_shows_placeholder_and_send_guides) is recut to
  `test_no_loaded_model_shows_placeholder_and_disables_send`, which pins
  the disabled button and Enter-inserts-newline instead of the guide.
* **AC-153:** Ctrl+Enter / Cmd+Enter sending is retired; superseded by
  AC-168. Both old send tests are recut to the no-op form.
* **AC-154:** the empty / whitespace-only keyboard guard is retired with
  the shortcut (superseded by AC-168); the old test is removed from the
  suite by absence.
* **AC-155:** the shortcut-stating placeholder is retired; superseded by
  AC-169; the old test is recut to assert the newline-only placeholder.

## Changed files

* `src/static/app.js` — the composer keydown handler (Ctrl+Enter / Cmd+Enter
  -> `form.requestSubmit()`) is removed; the Send-button click remains the
  only submit path. No other submit logic changed (AC-152's Enter-newline is
  the textarea default).
* `src/static/index.html` — the message-input placeholder recut to
  "Type a message... (Enter for newline)".

## Test-to-file mapping

Now-approved node IDs pin exactly:

* `tests/test_ui.py::test_no_loaded_model_shows_placeholder_and_disables_send[chromium]` (recut from ..._send_guides)
  -> `src/static/app.js` (AC-130)
* `tests/test_ui.py::test_message_input_ctrl_enter_does_not_send[chromium]` (recut from ..._sends)
  -> `src/static/app.js` (AC-168)
* `tests/test_ui.py::test_message_input_cmd_enter_does_not_send[chromium]` (recut from ..._sends)
  -> `src/static/app.js` (AC-168)
* `tests/test_ui.py::test_message_input_placeholder_states_newline_only[chromium]` (recut from ..._shortcuts)
  -> `src/static/index.html` (AC-169)

Contracts: `files` gains `src/static/index.html` (the placeholder oracle's
owner); `changed_files` lists `src/static/app.js` and `src/static/index.html`
(this freeze's inventory); no entry_points, routes, schemas, errors, ui,
externals, or smoke checks change.