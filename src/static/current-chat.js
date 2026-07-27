// M31 — current-chat awareness (AC-111..AC-126).
//
// Owns the header title for the active thread: display, inline rename, and
// the two-way sync with the sidebar row. Kept out of app.js deliberately —
// app.js already carries model selection, streaming, and modal wiring.
window.CurrentChat = (function () {
  var TC = window.TC;

  function el(id) { return document.getElementById(id); }

  var editing = false;
  var editThreadId = null;

  function activeThread() {
    return TC.threads.find(function (t) { return t.id === TC.activeThreadId; });
  }

  function sidebarTitleEl(id) {
    var row = document.querySelector(
      '[data-testid="thread-item"][data-thread-id="' + id + '"]'
    );
    return row ? row.querySelector('.thread-title') : null;
  }

  // AC-111: header title mirrors the active thread. AC-112: the full string
  // stays reachable through the native tooltip when CSS truncates it.
  // AC-125: textContent, never innerHTML — a title is user-supplied text.
  function refresh() {
    var span = el('current-thread-title');
    if (!span || editing) return;
    var thread = activeThread();
    var text = thread ? thread.title : '';
    span.textContent = text;
    span.setAttribute('title', text);
  }

  // AC-113: the input opens focused with the title pre-selected, so the first
  // keystroke replaces rather than appends.
  function beginEdit() {
    var thread = activeThread();
    var span = el('current-thread-title');
    var input = el('current-thread-title-input');
    if (!thread || !span || !input || editing) return;
    editing = true;
    editThreadId = thread.id;
    span.hidden = true;
    input.hidden = false;
    input.value = thread.title;
    input.focus();
    input.select();
  }

  function endEdit() {
    var span = el('current-thread-title');
    var input = el('current-thread-title-input');
    editing = false;
    editThreadId = null;
    if (input) input.hidden = true;
    if (span) span.hidden = false;
  }

  // AC-114/117/126: Enter and blur commit; whitespace-only reverts to the
  // prior title; newlines collapse so the row stays single-line.
  //
  // The sidebar row is patched in place rather than re-rendered: a full
  // renderSidebar() here would destroy the row between mousedown and mouseup
  // when the commit was triggered by a blur from clicking another thread,
  // and the switch click would land on a detached node (AC-118).
  function commit() {
    if (!editing) return;
    var id = editThreadId;
    var input = el('current-thread-title-input');
    var raw = input ? input.value : '';
    endEdit();
    var thread = TC.threads.find(function (t) { return t.id === id; });
    if (!thread) { refresh(); return; }
    var value = raw.replace(/[\r\n]+/g, ' ').trim();
    if (value) {
      thread.title = value;
      window.Threads.persistThreads();
      var rowTitle = sidebarTitleEl(id);           // AC-120: sidebar follows
      if (rowTitle) rowTitle.textContent = value;
    }
    refresh();
  }

  // AC-115: Escape discards the buffer and leaves the stored title alone.
  function cancel() {
    if (!editing) return;
    endEdit();
    refresh();
  }

  var titleEl = el('current-thread-title');
  var inputEl = el('current-thread-title-input');
  if (titleEl) titleEl.addEventListener('click', beginEdit);
  if (inputEl) {
    inputEl.addEventListener('keydown', function (e) {
      e.stopPropagation();
      if (e.key === 'Enter') { e.preventDefault(); commit(); }
      if (e.key === 'Escape') { e.preventDefault(); cancel(); }
    });
    inputEl.addEventListener('blur', commit);
  }

  return {
    refresh: refresh,
    // AC-118: a thread switch commits whatever edit is open first.
    commitPending: commit
  };
})();
