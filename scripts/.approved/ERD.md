ERD — testchat M13: Module Split (erd_version 27)

What changes v26 -> v27

File inventory updated: two new files (markdown.js, threads.js) added to
contracts. Smoke_checks added for both. No code changes — files already exist.

File inventory (M13 build) — DAG order

1. src/static/style.css — NO EDIT NEEDED
2. src/static/markdown.js — NO EDIT NEEDED (already exists, exports window.MD)
3. src/static/threads.js — NO EDIT NEEDED (already exists, exports window.TC + window.Threads)
4. src/static/app.js — NO EDIT NEEDED (already uses MD/Threads/TC)

Contract ids per task: contracts = [] for all (frontend files).

Oracle Mapping: all browser node-ids map to src/static/app.js (final in DAG).
Smoke_checks cover the two new files.

Test dependencies: none new.
