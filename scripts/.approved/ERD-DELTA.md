# ERD-DELTA v104 — composer keyboard send (Enter-to-send)

Behavioral re-freeze: the v102 design retired every keyboard send path (Send
button only). This delta reverses that decision for plain Enter only — the
CEO ruling (2026-08-14): plain Enter must send; Shift+Enter is the newline.
The app behavior is NOT yet implemented on this tree; the freeze pins the
acceptance criteria and the UI oracle first (INV-1 — tests before code), and
the direct fix (one keydown handler + one placeholder) lands after the
freeze as a routed fix.

## Changed acceptance criteria

* **AC-152 (amended):** plain Enter (no Shift/Ctrl/Cmd, no IME composition)
  SENDS the message through the same dispatch path the Send button takes,
  instead of inserting a newline.

* **AC-168 (amended):** the dispatch paths are now the Send button AND plain
  Enter; Shift+Enter inserts a newline only; Ctrl+Enter / Cmd+Enter remain
  non-sending. The v102 "Send button is the ONLY path" clause is superseded.

* **AC-169 (amended):** the placeholder recuts to "Type a message... (Enter
  to send, Shift+Enter for newline)" — it now advertises the Enter-to-send
  shortcut and the Shift+Enter newline behavior.

* **AC-130 (amended):** the no-model guard is reachable by keyboard again —
  a plain-Enter send attempt with nothing loaded fires the "Pick a model
  from the dropdown before sending." error bubble (the submit guard) and
  dispatches nothing; the disabled Send control remains the standing
  affordance. AC-131 stays retired as a standing affordance; its guard-text
  revival is noted in the PRD.

## Superseded acceptance criteria

* **AC-152 (v102 form):** "Enter inserts a newline at the cursor and never
  sends" — superseded by the v104 amendment; plain Enter now dispatches.
* **AC-168 (v102 form):** "the Send button is the ONLY path that dispatches;
  no keyboard combination sends" — superseded; plain Enter is now a dispatch
  path, Shift+Enter is newline-only, Ctrl/Cmd+Enter stay no-ops.
* **AC-169 (v102 form):** placeholder "Type a message... (Enter for
  newline)" with no advertised shortcut — superseded; the placeholder now
  advertises Enter-to-send and Shift+Enter newline.

## Changed files

* `src/static/app.js` — adds a keydown handler on the message input: plain
  Enter (no modifier keys, no IME composition) dispatches the form's submit
  event (the same path the Send button's click takes, including the
  no-model / unloaded-model guards); Shift+Enter and Ctrl/Cmd+Enter are left
  to the textarea default (newline / nothing). No other submit logic
  changes.
* `src/static/index.html` — the message-input placeholder recut to
  "Type a message... (Enter to send, Shift+Enter for newline)".

## Test-to-file mapping

Now-approved node IDs pin exactly:

* `tests/test_ui.py::test_no_loaded_model_shows_placeholder_and_disables_send[chromium]` (recut — guard bubble + no dispatch)
  -> `src/static/app.js` (AC-130)
* `tests/test_ui.py::test_message_input_plain_enter_sends[chromium]` (recut from ..._inserts_newline_without_sending)
  -> `src/static/app.js` (AC-152)
* `tests/test_ui.py::test_message_input_shift_enter_inserts_newline_without_sending[chromium]` (recut from ..._plain_enter_...; new)
  -> `src/static/app.js` (AC-168)
* `tests/test_ui.py::test_message_input_placeholder_states_send_shortcut[chromium]` (recut from ..._states_newline_only)
  -> `src/static/index.html` (AC-169)

Carried unchanged (comment-only edits, D-116): the Ctrl+Enter and Cmd+Enter
no-op tests — both modifiers remain non-sending under v104.

Contracts: `changed_files` lists `src/static/app.js` and `src/static/index.html`
(this freeze's inventory); `files` is unchanged (both already present); no
entry_points, routes, schemas, errors, ui, externals, or smoke checks change.
