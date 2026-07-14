ERD — testchat M22: Count Only Visible Search Hits (erd_version 40)

What changes v39 -> v40

One file, one edit: threads.js filters the collected hit list to visible
elements.

File inventory (M22 build) — DAG order

1. src/static/threads.js — EDIT. In highlightSearchHits(), the collection
   statement currently reads exactly:
   `hitElements = document.querySelectorAll('mark.search-hit');`
   Replace ONLY that statement with one that keeps just the visible marks:
   `hitElements = Array.prototype.filter.call(document.querySelectorAll('mark.search-hit'), function (m) { return m.getClientRects().length > 0; });`
   (An element hidden inside a collapsed thinking section has no client
   rects.) Nothing else in the file changes — hitElements is already used
   only via .length and index access, which arrays support.

Contract ids per task: contracts = [] — an EMPTY list. NEVER invent
module-style ids.

Oracle Mapping: no new node-ids. ALL browser node-ids are carried forward —
do NOT map them (the shell auto-assigns regression, D-57).

Test dependencies: none new.
