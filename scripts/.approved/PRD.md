PRD — testchat M10: Ratify the Sprint (freeze coverage for the live-fix features)

Milestone

Between v19 and this freeze, a series of CEO-directed live sessions shipped
real features outside the pipeline (commits labeled "[live-fix, CEO
session]"): markdown rendering, three themes, thread rename/delete with
auto-retitle, a stop button, a streaming cursor and render throttle, a
status strip, per-bubble chrome, the Nemotron crash fix, and an app-wide
system prompt. They work — verified live and by the untouched 84-test
suite — but nothing DEFENDS them: no acceptance criteria, no frozen tests,
no locked surface. This milestone adds no new behavior. It ratifies the
sprint: every user-facing live-fix feature gains frozen acceptance
criteria, browser/backend tests, and locked testids, so the next build
cannot silently regress them (the M5/M6 lesson, applied at scale).

The only code changes are data-testid attributes on controls the new
tests must reach.

What

- src/static/index.html: testids on the settings-modal controls
  (system-prompt-input, settings-save, settings-cancel) and the status
  strip. The gear and theme buttons already carry theirs.
- src/static/app.js: testids on the dynamically created per-thread
  rename/delete buttons and the inline rename input.
- Frozen artifacts: AC-44..AC-52 below, six new browser tests, two new
  backend test files, and the settings/status routes + nine testids
  entering the locked contracts.

Acceptance Criteria (EARS notation)

All prior criteria remain in force. AC-44..AC-49 are frozen Playwright UI
tests (D-58); AC-50..AC-52 are frozen backend tests.

AC-44 (markdown): WHEN an assistant reply contains markdown emphasis or
inline code, THE SYSTEM SHALL render it formatted — the marked text
visible, the markup characters (** and `) not displayed.

AC-45 (themes): WHEN the user clicks the theme toggle, THE SYSTEM SHALL
switch the page theme, and WHEN the page is reloaded, THE SYSTEM SHALL
restore the last selected theme.

AC-46 (rename): WHEN the user activates a thread's rename control, edits
the title, and confirms with Enter, THE SYSTEM SHALL display and persist
the new title.

AC-47 (delete): WHEN the user activates a thread's delete control and
confirms the dialog, THE SYSTEM SHALL remove that thread from the sidebar
and its stored snapshot.

AC-48 (stop): WHILE a reply is streaming, THE SYSTEM SHALL present the
send control as "Stop"; WHEN the user clicks it after visible text has
arrived, THE SYSTEM SHALL end the stream, keep the partial reply in the
thread, and restore the "Send" control.

AC-49 (system prompt, end to end): WHEN a system prompt has been saved via
the settings modal, THE SYSTEM SHALL send it as the first message (role
"system") of every subsequent chat request.

AC-50 (settings API): GET /api/v1/settings returns the saved prompt
(empty string when none); PUT stores it; a corrupt or missing settings
file reads as empty rather than failing.

AC-51 (system-prompt precedence): WHEN the LLM_SYSTEM_PROMPT env var is
set — including set-but-empty — THE SYSTEM SHALL use it and ignore the
UI-saved prompt; WHEN it is unset, THE SYSTEM SHALL use the UI-saved
prompt.

AC-52 (status API): GET /api/v1/status returns HTTP 200 with a JSON
object (the UI status strip's data source).

manual-only waivers (D-58):
- Per-bubble hover chrome (copy button, message-pair delete, time/model
  badge): clipboard access and hover-reveal pseudo-content are
  environment-dependent in headless runs; CEO-demo verified.
- Auto-retitle heuristic (generic titles replaced from the first reply):
  heuristic by design; CEO-demo verified; deliberately not pinned so the
  heuristic can evolve.
- Streaming render throttle and stream cursor: implementation qualities,
  not behaviors; their absence would surface in the CEO demo as jank.
- Nemotron crash-dialog fix: OS-process behavior outside the sandbox;
  verified over live load/unload cycles.
- Matrix/CRT theme visual treatment: appearance is design, not behavior;
  AC-45 pins the mechanism only.

Out of Scope

New behavior of any kind. Visual changes. The system-prompt modal's
keyboard shortcuts. Multi-user settings.

Flagged Assumptions (CEO sign-off at the freeze gate)

A17: Ratifying tests pin behavior as it exists today, quirks included —
they are written to PASS on the current tree (unlike feature freezes,
where tests fail first). The proof obligation inverts: I verified each new
test red against a tree WITHOUT the feature only where cheap (testids),
and otherwise rely on assertions that cannot pass vacuously.
A18: The stop test uses a deliberately slow stub model in the test
fixture; no production code knows about it.

CEO Demo Script (spot checks — the suite is the real gate now)

Toggle theme, reload — theme kept. Rename a thread, delete a thread.
Ask for "a **bold** word" — see bold, no asterisks. Set a pirate system
prompt, ask anything — reply obeys; clear it. Stop a slow reply midway —
partial stays. Status strip shows your model and tok/s while streaming.
