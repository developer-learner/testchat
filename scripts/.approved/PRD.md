PRD — testchat M13: Module Split (ratify file inventory)

Milestone

M13 ratifies the app.js module split that landed as a CEO-directed live-fix.
The 995-line IIFE was split into three files sharing state via window.TC:
- markdown.js (window.MD): pure text-to-HTML transforms
- threads.js (window.Threads): thread CRUD, sidebar, bubble chrome
- app.js: init, streaming, settings, status, themes, fullscreen, models

No behavior change. The frozen test suite exercises all functionality through
the browser; the module boundaries are internal. This milestone adds the new
files to the contracts file inventory with smoke_checks.

Acceptance Criteria

All v26 criteria remain in force. No new ACs — the split is structural, not
behavioral.

Out of Scope: new features, test changes.

CEO Demo Script: Already accepted — CEO verified the split in-browser on
2026-07-12. This milestone is paperwork.
