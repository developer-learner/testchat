PRD — testchat M14: Rain Relocation (ratify)

Milestone

M14 ratifies a CEO-directed live-fix (commits 33e93b0, 470ad0f): the digital
rain backdrop was rewritten (delta-time animation, DPR support, Vercel-style
overlay, measured column spacing) and relocated from the phosphor theme to
the matrix theme. Phosphor keeps its scanlines, glow, and monospace look but
no longer shows rain; matrix is now the sole animated theme.

The code is already correct and CEO-accepted live — every implementation
file needs NO EDIT. This milestone updates the oracle to match.

Acceptance Criteria

- AC-54 (revised): WHEN the matrix theme is active, the system SHALL display
  the full-screen digital-rain canvas backdrop; WHEN any other theme is
  active, the backdrop SHALL be hidden.

All other v27 criteria remain in force unchanged.

Out of Scope: theme merging, new themes, phosphor terminal-window layout
(queued as M11c), any behavior change.

CEO Demo Script: Already accepted in live sessions on 2026-07-13 — CEO
directed the relocation and verified rain-in-matrix / no-rain-in-phosphor
in-browser. This milestone is paperwork.
