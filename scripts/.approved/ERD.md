ERD — testchat M26: Web Search Ratify (erd_version 49)

What changes v48 -> v49 (v48 was authored over-scoped and never
successfully ran a plan; v49 is the correct ratify shape.)

Pure spec-catch-up ratify (D-63). The tree already carries every M25
live-fix; the pipeline run here is a coder no-op. The M26 delta is
SPEC-ONLY: no file is added to or removed from the build inventory
(same 10 files as v47), so no test that was regression under v47
becomes "delta inventory" under v49 (which was v48's over-scope defect).
Behavior newly locked:

- AC-90 wiring — src/main.py loads .env at import via python-dotenv
  (live-fix `d093a55`). Pinned by the existing
  test_websearch_api::test_status_reports_web_configured (regression)
  plus a smoke_check note in this ERD (main.py is NOT added to the
  inventory — this ratify does not turn the app entry-point into a
  gated task).
- AC-92 citation transform — `renderReply` in src/static/app.js
  normalizes Qwen full-width markers `【N†anchor】` to `[N]` before
  render (live-fix `ebbaa75`). Pinned by
  test_ui_websearch::test_full_width_citation_markers_render_as_plain_brackets
  (regression band) AND a strengthened smoke_check that greps for
  `【` in app.js (the character only appears there because of the
  regex).
- AC-93 prompt cite instruction — `build_prompt` in
  src/services/websearch.py names plain `[N]` brackets and prefers the
  most specific/recent number when sources disagree (live-fix
  `ebbaa75`). Pinned by
  test_websearch_service::test_prompt_forbids_full_width_citations
  (regression band) AND a strengthened smoke_check that greps for
  `plain square`.

File inventory (M26 build) — UNCHANGED from v47

Same 10 files as v47. Same no_edit_files as v47 (markdown.js, rain.js,
style.css). No tasks are needed for this ratify: no file's build
inventory changes; every task that WOULD be emitted would be a no_edit
no-op for a file that already carries the ratified behavior.

DAG: EMPTY. The EM MUST emit an empty plan (`{"erd_version": 49,
"tasks": []}`). The validator accepts an empty plan when the frozen
tests satisfy the whole delta as regression — which they do here: the
two new test node-ids are auto-carried by D-57 regression assignment,
and the AC-90/92/93 smoke_checks live in contracts.json (checked at
freeze, not run-time).

Contract ids per task: N/A (no tasks).

Oracle Mapping — no new mappings; two new node-ids ride as regression:
- tests/test_websearch_service.py::test_prompt_forbids_full_width_citations
  (regression — no mapping; observes only websearch.py which is not
  in this delta's edit scope)
- tests/test_ui_websearch.py::test_full_width_citation_markers_render_as_plain_brackets
  (regression — no mapping; observes only app.js which is not in this
  delta's edit scope)
ALL other node-ids are carried forward — do NOT map them.

Test dependencies: no new externals; no new stack imports. The new
UI test seeds a prepared assistant message via the locked PUT
/api/v1/threads route and verifies renderThreadMessages transforms the
marker on reload — avoiding an LLM stub change.
