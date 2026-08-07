# ERD-DELTA — spec v86

The current milestone's slice of the spec. THIS FILE IS THE D-107 ERD-DELTA
referred to by the EM prompt: the pending change is contracts.ui pinning (the
D-120 slot of the milestone view, remaining after the contracts block audit).

## Changed acceptance criteria
None — no product behavior changes in this freeze.

## Superseded acceptance criteria
None.

## Changed files
None — contracts.changed_files stays empty: the ui file pins are spec
metadata (ownership of frozen testids), not product code.

## Test-to-file mapping
Unchanged — the v84 mapping remains frozen data in contracts.test_mapping.

## contracts.ui pinning (D-120 slot, v86)
Every `ui:*` testid in contracts.json pins its behavioral-owner file (the
script whose logic drives the element), matching routes/schemas/errors pins
landed in v83:
- app.js: new-thread-btn, message-input, send-btn, think-toggle, msg-user,
  msg-assistant, load-confirm+modal/cancel, status-strip, web-toggle, msg-error
- threads.js: thread-item, delete-confirm+modal+cancel, thread-rename-btn,
  thread-rename-input, thread-delete-btn, thread-search-input, search-hit,
  search-hit-count, search-prev-btn, search-next-btn, save-status,
  history-status, msg-meta, msg-sources, source-link, web-notice
- catalog.js: model-select, eject-model-btn, unload-confirm+modal/cancel
- chrome.js: settings-toggle, theme-toggle, system-prompt-input,
  settings-save, settings-cancel, terminal-titlebar
- current-chat.js: current-thread-title, current-thread-title-input
- markdown.js: think-content; rain.js: matrix-rain
- sidebar-resize.js: sidebar-resizer

The D-120 milestone slice (scripts/contracts-delta.py) gains `ui` in its
pinned keys: out-of-inventory testids become a one-line out_of_scope index
(id + testid + pin); unpinned UI entries stay full (conservative carry).