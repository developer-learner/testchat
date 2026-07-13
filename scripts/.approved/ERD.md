ERD — testchat M12: Ratify the Sprint (erd_version 26)

What changes v25 -> v26

Spec-only update. No file inventory changes — both files (style.css, app.js)
already contain all ratified features. The sole code change is the frozen
test (AC-53/55: 5 to 10 theme cycle).

File inventory (M12 build) — DAG order

1. src/static/style.css — NO EDIT NEEDED (already contains all 10 theme
   blocks including neon, crisp, ember, graphite-amber, graphite-forest).
2. src/static/app.js — NO EDIT NEEDED (THEMES array already has 10 entries,
   all UI features already implemented).

The pipeline tasks for this milestone are no-ops — the code is already
correct. The only artifact that changes is the test suite.

Contract ids per task: contracts = [] for both (frontend files).

Oracle Mapping

- ALL browser node-ids (tests/test_ui.py::*) map to src/static/app.js task.
- The amended cycle test (ten themes) rides the same node-ids.

Test dependencies: none new.
