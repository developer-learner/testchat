ERD — testchat M16: Newest Thread First (erd_version 31)

What changes v30 -> v31

One behavioral edit in threads.js: renderSidebar() renders TC.threads in
REVERSE array order (last element first), so the newest thread appears at
the top of the sidebar. TC.threads storage order, persistence payloads, and
every other function stay exactly as they are — this is a render-order
change only.

File inventory (M16 build) — DAG order

1. src/static/index.html — NO EDIT NEEDED
2. src/static/style.css — NO EDIT NEEDED
3. src/static/markdown.js — NO EDIT NEEDED
4. src/static/threads.js — EDIT. In renderSidebar(), iterate TC.threads from
   the last index down to 0 (instead of 0 up), so items append newest-first.
   Change nothing else: the per-item construction (title, actions, rename,
   delete, click-to-switch handlers) stays identical.
5. src/static/app.js — NO EDIT NEEDED (final task)

Contract ids per task: contracts = [] — an EMPTY list, for ALL tasks.
Frontend files have no module entry points; NEVER invent module-style ids.

Task dependencies: the src/static/app.js task MUST list every other task in
its depends_on (it is the DAG's final task).

Oracle Mapping: ALL browser node-ids — including the new
tests/test_ui.py::test_sidebar_lists_newest_thread_first and the three
amended ones (model-lock, switch-restores-history, failed-reply-keeps) —
map to the src/static/app.js task, the DAG's final task. This is mechanical
law since D-64: a browser test maps only to a task whose dependency closure
contains the whole plan. Every file carries a smoke_check as its per-task
signal.

Test dependencies: none new.
