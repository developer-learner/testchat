ERD — testchat M18: Thread Search (erd_version 34)

What changes v33 -> v34

Three edits, all frontend: index.html gains the search input; threads.js
filters renderSidebar() by the query; style.css styles the box. No backend
change, no new routes, no persistence change.

File inventory (M18 build) — DAG order

1. src/static/index.html — EDIT. Inside the sidebar <aside>, directly ABOVE
   the thread-list div, add one input element: type "text", id
   "thread-search", class "thread-search", attribute
   data-testid="thread-search-input", placeholder "Search threads...".
   Nothing else changes.

2. src/static/style.css — EDIT. Style .thread-search using ONLY existing
   theme variables so every theme works: display block, width calc(100% -
   1.5rem), margin 0.4rem 0.75rem, padding 0.45rem 0.6rem, background
   var(--input-bg), color var(--input-text), border 1px solid
   var(--input-border), border-radius 6px, font inherit, font-size
   0.85rem. Add a :focus rule: outline none, border-color var(--accent).
   Nothing else changes.

3. src/static/threads.js — EDIT (two tightly-related changes):
   a) A module-level variable holding the current query, initialized to
      the empty string, plus one statement wiring it: an 'input' event
      listener on the element with id "thread-search" that lowercases and
      trims the field's value into that variable and then calls
      renderSidebar(). Guard the wiring so a missing element does not
      throw (if the element is null, skip attaching).
   b) In renderSidebar(), where it loops over TC.threads: when the query
      variable is non-empty, skip any thread that does not match. A thread
      matches when its title lowercased contains the query, OR any of its
      messages' content lowercased contains the query. The existing
      iteration order (newest first) and all per-item construction stay
      exactly as they are.

Contract ids per task: contracts = [] — an EMPTY list, for ALL tasks.
NEVER invent module-style ids.

Task dependencies: the src/static/threads.js task MUST list both other
tasks in its depends_on (it is the DAG's final task).

Oracle Mapping: the new browser node-id
tests/test_ui.py::test_sidebar_search_filters_threads maps to the
src/static/threads.js task (final in DAG, D-64 — its dependency closure
must contain the whole plan). All other browser node-ids are carried
forward — do NOT map them (the shell auto-assigns regression, D-57).

Test dependencies: none new.
