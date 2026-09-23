# ERD-DELTA v128 — T4 brief correction (planning-only)

Freeze context: v127 ran under `swbp orchestrate`. T1, T2, T3, T5, T6 and T7
passed. T4 (`src/static/threads.js`) failed twice and escalated: the coder
built every per-chat piece correctly but wrote `_doThreadMutation` by copying
the neighbouring whole-history `_doPersistPut` — it posts all chats to
`/api/v1/threads` with the envelope revision. The EM's `decomposition_wrong`
verdict (blaming the hydration guard) is not supported: the guard change is
correct and the reference build passes with it. This freeze is planning-only:
it restates T4's brief with the exact function, and pins the carried browser
tests still in the milestone's scope to the last task. No test, contract or
acceptance criterion changes.

## Changed acceptance criteria

None. AC-189 … AC-207 stand as frozen in v127.

## Superseded acceptance criteria

None.

## Changed files

- `src/static/threads.js` — T4 brief restated (planning-only; the file is in
  v127's inventory). No other file is touched.

## Coder briefs (verbatim)

### T4 — src/static/threads.js (per-chat save request)

The per-chat pieces are already in the file: `_savedThreads`, `_threadRevisions`, `_fingerprint`, `_threadPayload`, `markHydrated`, the `THREAD_PUT`/`THREAD_DELETE` dispatch in `_drainPersistQueue`, `persistThreads`, the `deleteThread` call and the `markHydrated` export. Only `_doThreadMutation` is wrong: it posts the whole history. Replace the entire `function _doThreadMutation(entry) { ... }` with exactly this code, which also adds `_threadSaveFailed` right after it:

```
  function _doThreadMutation(entry) {
    var id = entry.payload.id;
    var isPut = entry.type === 'THREAD_PUT';
    var body = { revision: _threadRevisions[id] || 0 };
    if (isPut) body.thread = entry.payload.thread;
    fetch('/api/v1/threads/' + id, {
      method: isPut ? 'PUT' : 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    }).then(function (res) {
      if (res.status === 409) {
        return res.json().then(function () { _handleConflict(); });
      }
      if (!res.ok) { _threadSaveFailed(id); return; }
      return res.json().then(function (data) {
        if (isPut) { _threadRevisions[id] = data.revision; } else { delete _threadRevisions[id]; }
        el('status-save').textContent = '';
        _persistQueue.shift();
        _persistRunning = false;
        _drainPersistQueue();
      });
    }).catch(function () { _threadSaveFailed(id); });
  }

  function _threadSaveFailed(id) {
    el('status-save').textContent = 'not saved';
    delete _savedThreads[id];
    _persistQueue.shift();
    _persistRunning = false;
    _drainPersistQueue();
  }
```

Self-verify: `_doThreadMutation` fetches `'/api/v1/threads/' + id`, sends `revision: _threadRevisions[id] || 0`, and reads neither `_hydratedRevision` nor `_captureSnapshot`.

## Task DAG

Task order: T4 (threads.js)

## Test-to-file mapping

* `tests/test_ui.py::test_bubble_meta_includes_date_for_past_messages`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_click_header_title_enters_edit_mode`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_current_thread_is_highlighted_in_sidebar`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_current_thread_title_shows_in_header`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_empty_header_title_commit_reverts_to_prior`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_enter_commits_header_title_edit`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_escape_reverts_header_title_edit`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_failed_reply_keeps_user_message`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_header_rename_updates_sidebar_row_immediately`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_header_title_updates_when_switching_threads`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_highlight_moves_when_current_thread_deleted`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_highlight_moves_when_switching_threads`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_history_quarantine_indicator_shows`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_history_sent_to_backend_has_no_think_markup`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_history_status_empty_when_healthy`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_long_header_title_truncates_with_full_text_in_tooltip`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_markdown_renders_readably`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_message_input_cmd_enter_does_not_send`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_message_input_ctrl_enter_does_not_send`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_message_input_placeholder_states_send_shortcut`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_message_input_plain_enter_sends`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_message_input_shift_enter_inserts_newline_without_sending`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_mid_chat_switch_updates_thread_model_and_routes_next_send`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_model_option_labels_never_carry_checkmark`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_new_chat_creates_unlocked_empty_thread`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_newlines_in_header_title_are_stripped_on_commit`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_no_loaded_model_shows_placeholder_and_disables_send`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_rain_backdrop_only_in_matrix`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_reload_after_current_deleted_opens_newest_remaining`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_reload_opens_newest_thread`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_reply_copy_source_strips_think_after_reload`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_saved_system_prompt_reaches_requests`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_search_hit_count_and_navigation`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_search_hits_highlighted_in_open_thread`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_selector_stays_enabled_across_all_ui_states`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_sidebar_divider_drags_and_clamps`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_sidebar_lists_newest_thread_first`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_sidebar_rename_updates_header_immediately`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_sidebar_search_filters_threads`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_sidebar_width_persists_across_reload`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_stop_button_keeps_partial_reply`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_switching_threads_mid_edit_commits_pending_rename`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_terminal_titlebar_only_in_phosphor`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_theme_cycle_reaches_phosphor_and_wraps`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_theme_switch_persists_across_reload`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_think_toggle_reveals_and_hides_thinking`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_thinking_placeholder_shows_then_clears`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_thread_delete_removes_thread`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_thread_model_selection_persists_across_reload_without_send`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_thread_rename_via_sidebar_control`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_thread_switch_restores_history`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_thread_switch_restores_stored_model`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_thread_title_set_from_first_message`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_thread_title_stores_full_text_beyond_thirty_chars`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_threads_survive_reload`
  -> `src/static/threads.js`
* `tests/test_ui.py::test_title_renders_as_text_not_html`
  -> `src/static/threads.js`
