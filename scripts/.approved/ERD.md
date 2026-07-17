ERD — testchat M26: Web Search Ratify (erd_version 48)

What changes v47 -> v48

Ratify milestone (D-63): every M25 live-fix is already in the tree.
The pipeline run for this freeze is a coder no-op — every file in the
inventory carries "NO EDIT NEEDED". The frozen tests catch up: three
new tests pin the ratified behavior (AC-92 citation transform,
AC-93 prompt cite instruction, AC-90 .env boot-load).

File inventory (M26 build) — all NO EDIT NEEDED

1. src/main.py — NO EDIT NEEDED. Already loads `.env` via
   `python-dotenv` at import (live-fix `d093a55`). Behavior pinned by
   AC-90.
2. src/services/websearch.py — NO EDIT NEEDED. `build_prompt` already
   instructs plain `[N]` citations and "prefer the most specific/recent
   number when sources disagree" (live-fix `ebbaa75`). Behavior pinned
   by AC-93.
3. src/static/app.js — NO EDIT NEEDED. `renderReply` already normalizes
   `【N†anchor】` → `[N]` before markdown render (live-fix `ebbaa75`).
   Behavior pinned by AC-92 via a UI test.
4. src/static/style.css — NO EDIT NEEDED. Web-toggle armed/disabled
   states and source-link list styling landed (live-fixes `a7b0c33`,
   `efdd174`). No AC — visuals are CEO-eyeball, D-44 already accepted.
5. src/api/status.py — NO EDIT NEEDED (v47).
6. src/api/chat.py — NO EDIT NEEDED (v47).
7. src/api/threads.py — NO EDIT NEEDED (v47).
8. src/static/index.html — NO EDIT NEEDED (v47).
9. src/static/threads.js — NO EDIT NEEDED (v47).
10. src/static/markdown.js — NO EDIT NEEDED (v47).
11. src/static/rain.js — NO EDIT NEEDED (v47).

no_edit_files (D-65 — every file this milestone; the coder is never
called):
src/services/websearch.py, src/api/status.py, src/api/chat.py,
src/api/threads.py, src/main.py, src/static/index.html,
src/static/threads.js, src/static/app.js, src/static/markdown.js,
src/static/rain.js, src/static/style.css

Contract ids per task: contracts = [] (empty for every no-op task).

Oracle Mapping — two NEW node-ids this milestone:
- tests/test_websearch_service.py::test_prompt_forbids_full_width_citations
  -> maps to the src/services/websearch.py task (no_edit acceptance —
  AC-93).
- tests/test_ui_websearch.py::test_full_width_citation_markers_render_as_plain_brackets
  -> maps to the src/static/app.js task (no_edit acceptance — AC-92).
ALL other node-ids are carried forward — do NOT map them.

Test dependencies: no new externals; no new stack imports (dotenv
already in requirements.txt since M8). The new UI test seeds a
prepared assistant message via PUT /api/v1/threads (locked route) and
verifies renderThreadMessages transforms the marker on reload —
avoiding an LLM stub change.
