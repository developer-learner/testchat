ERD — testchat M19: Search-Hit Highlighting (erd_version 35)

What changes v34 -> v35

Two edits: threads.js applies/removes the highlights; style.css styles
them. No markup change (the highlight elements are created at render time),
no backend change.

File inventory (M19 build) — DAG order

1. src/static/style.css — EDIT. Add a rule for mark.search-hit: background
   var(--accent), color var(--accent-contrast), border-radius 3px, padding
   0 2px. Nothing else changes.

2. src/static/threads.js — EDIT (one concern: highlight application).
   a) New module-level function highlightSearchHits(). Behavior: it
      operates on the element with id "chat-container". First it does
      nothing further if threadSearchQuery is empty. Otherwise it walks
      ALL TEXT NODES under the container (document.createTreeWalker with
      NodeFilter.SHOW_TEXT), and for each text node whose text contains
      threadSearchQuery case-insensitively, it replaces that text node
      with a sequence of nodes where every matched substring is wrapped
      in an element: <mark> with class "search-hit" and attribute
      data-testid="search-hit" (preserve the original character casing of
      the matched substring; non-matching segments stay plain text nodes).
      Never touch element attributes or HTML source strings — only text
      nodes, so existing markdown-rendered markup cannot be corrupted.
      Skip text nodes inside <mark> elements to stay idempotent. After
      wrapping, if at least one mark was created, call scrollIntoView
      on the first one (block 'center').
   b) Call highlightSearchHits() at the end of switchThread() (after
      renderThreadMessages and restoreThreadModelState run for a found
      thread).
   c) In the existing 'input' listener on the thread-search element:
      after the existing renderSidebar() call, re-render the open
      thread's messages exactly the way deleteMessage() does it (clear
      chat-container innerHTML, toggle show-thinking class, call
      renderThreadMessages on the active thread if one exists), then
      call highlightSearchHits(). This both applies highlights live
      while typing and removes them when the box is emptied (the
      re-render rebuilds clean content; with an empty query the
      function adds nothing back).
   Everything else in the file stays exactly as it is.

Contract ids per task: contracts = [] — an EMPTY list, for BOTH tasks.
NEVER invent module-style ids.

Task dependencies: the src/static/threads.js task MUST list the style.css
task in its depends_on (it is the DAG's final task).

Oracle Mapping: the new browser node-id
tests/test_ui.py::test_search_hits_highlighted_in_open_thread maps to the
src/static/threads.js task (final in DAG, D-64). All other browser
node-ids are carried forward — do NOT map them (D-57).

Test dependencies: none new.
