ERD — testchat M20: Search-Hit Count and Navigation (erd_version 36)

What changes v35 -> v36

Three edits: index.html gains the nav row markup; style.css styles it and
the current-hit emphasis; threads.js gains the hit-tracking/cycling logic.

File inventory (M20 build) — DAG order

1. src/static/index.html — EDIT. Directly BELOW the existing thread-search
   input, add one div: class "search-hit-nav", attribute hidden. Inside it,
   in order: a button type "button" class "hit-nav-btn" with
   data-testid="search-prev-btn" and text ▲; a span with
   data-testid="search-hit-count" (empty); a button type "button" class
   "hit-nav-btn" with data-testid="search-next-btn" and text ▼. Nothing
   else changes.

2. src/static/style.css — EDIT (two related additions):
   a) .search-hit-nav: display flex, align-items center, gap 0.4rem,
      margin 0.15rem 0.75rem 0.4rem, color var(--sidebar-text), font-size
      0.75rem. .search-hit-nav[hidden] { display: none; }. .hit-nav-btn:
      background transparent, border 1px solid var(--sidebar-border),
      color var(--sidebar-text), border-radius 4px, cursor pointer,
      padding 0 0.35rem, font-size 0.7rem.
   b) mark.search-hit.current: background var(--accent-hover), outline
      2px solid var(--accent). Nothing else changes.

3. src/static/threads.js — EDIT (one concern: hit navigation). The file
   already has highlightSearchHits() (M19), which wraps matches in
   mark.search-hit elements and scrolls to the first. Changes:
   a) Two module-level variables: an array holding the current hit
      elements (init []), and a current index (init 0).
   b) At the end of highlightSearchHits(): collect all mark.search-hit
      elements inside chat-container into the array (document order),
      set index 0, then call a new function updateHitNav().
      highlightSearchHits() must also handle the empty-query case by
      clearing the array before returning. Its existing scroll-to-first
      behavior is replaced by updateHitNav()'s scrolling.
   c) New function updateHitNav(): finds the .search-hit-nav element
      (guard null). If the query is empty, set its hidden attribute and
      return. Otherwise remove the hidden attribute, set the
      search-hit-count span's textContent to (array.length ? (index+1) +
      "/" + array.length : "0/0"). Remove class "current" from every
      hit, and when the array is non-empty add class "current" to the
      hit at the current index and scrollIntoView it (block 'center').
   d) New function gotoHit(delta): if the array is empty do nothing;
      otherwise add delta to the index modulo the array length (wrapping
      both directions, keep it non-negative), then call updateHitNav().
   e) Wiring, next to the existing thread-search listener wiring and
      guarded the same way (skip if elements are null): click listener
      on [data-testid="search-prev-btn"] calling gotoHit(-1), and on
      [data-testid="search-next-btn"] calling gotoHit(1).
   Everything else stays exactly as it is.

Contract ids per task: contracts = [] — an EMPTY list, for ALL tasks.
NEVER invent module-style ids.

Task dependencies: the src/static/threads.js task MUST list both other
tasks in its depends_on (it is the DAG's final task).

Oracle Mapping: the new browser node-id
tests/test_ui.py::test_search_hit_count_and_navigation maps to the
src/static/threads.js task (final in DAG, D-64). All other browser
node-ids are carried forward — do NOT map them (D-57).

Test dependencies: none new.
