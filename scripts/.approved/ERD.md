ERD — testchat M23: Honest Saves (erd_version 44)

What changes v41 -> v42

Spec correction only (no code-facing changes beyond v41): every
no_edit_files entry now carries a smoke_check in contracts — a no-edit
task still needs an acceptance signal (v41 left four tasks unsatisfiable;
the EM halted correctly). Original v41 design below, unchanged.

What changed v40 -> v41

Three files change, each a small anchored edit. Four more frontend files
enter the inventory as no_edit_files (declared unchanged, D-65). The DAG
below is the required order.

File inventory (M23 build) — DAG order

1. src/api/threads.py — EDIT (two related edits, one task). The import
   block currently starts with exactly:
   `from fastapi import APIRouter`
   Insert ABOVE it a new first line:
   `from typing import Literal`
   The HistoryEntry model currently contains exactly:
   `    role: str`
   Replace ONLY that line with:
   `    role: Literal["user", "assistant"]`
   Nothing else in the file changes. FastAPI then returns 422 for any
   other role value automatically (AC-77) — write no validation code.

2. src/static/index.html — EDIT. The status strip currently contains
   exactly:
   `        <span id="status-ram"></span>`
   Insert directly BELOW that line:
   `        <span id="status-save" data-testid="save-status"></span>`
   Nothing else in the file changes.

3. src/static/threads.js — EDIT — the DAG's FINAL task: depends on
   EVERY other task (1, 2, and all four no_edit tasks). In
   persistThreads(), the fetch call currently ends with exactly:
   `    }).catch(function () {});`
   Replace ONLY that line with:
   `    }).then(function (res) {
      el('status-save').textContent = res.ok ? '' : 'not saved';
    }).catch(function () {
      el('status-save').textContent = 'not saved';
    });`
   The el() helper already exists at the top of this file. Nothing else
   in the file changes. (AC-75: non-2xx lands in .then with res.ok false;
   network failure lands in .catch. AC-76: the next successful persist
   writes '' through the same .then.)

no_edit_files (D-65 — never sent to the coder, acceptance still runs):
src/static/app.js, src/static/markdown.js, src/static/rain.js,
src/static/style.css

Contract ids per task: contracts = [] — an EMPTY list for ALL tasks,
including src/api/threads.py. NEVER invent module-style ids.

Oracle Mapping — three NEW node-ids this milestone:
- tests/test_threads_api.py::test_put_invalid_role_rejected
  -> maps to the src/api/threads.py task.
- tests/test_ui.py::test_save_failure_indicator_shows_then_clears
  -> maps to the src/static/threads.js task, which MUST be the DAG's
  final task: its depends_on MUST list EVERY other task id in the plan
  (the two edit tasks AND all four no_edit tasks). D-64: a browser test
  is accepted only downstream of the whole inventory. Transcribe these
  edges literally; do not infer or omit any.
ALL other node-ids are carried forward — do NOT map them (the shell
auto-assigns regression, D-57).

Test dependencies: the browser test exercises the save-status element
(new testid, locked in contracts.ui) and intercepts PUT /api/v1/threads
(already a locked route). No new externals; no new stack imports.
