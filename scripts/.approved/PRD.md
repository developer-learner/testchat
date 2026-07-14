PRD — testchat M21: Distinct Current-Hit Emphasis

Milestone

CEO demo of M20 failed AC-72's intent: the "current" search hit is styled
almost identically to every other hit (two sibling shades of the accent
color), so arrow navigation reads as aimless scrolling — you cannot see
WHICH match the pointer is on. M21 fixes the emphasis: ordinary hits get a
subtle tint; the current hit gets a loud, high-contrast one. Appearance
only — no behavior change.

Acceptance Criteria

- AC-73 (manual-only: relative visual emphasis is appearance, D-58): WHILE
  navigating hits, ordinary hits SHALL read as a subtle tint and the
  current hit SHALL be unmistakably distinct in every theme. Verified in
  the CEO demo.
- All existing ACs unchanged; the existing frozen tests are the regression
  oracle (mark.search-hit and the nav still exist and function).

Out of Scope: behavior changes, markup changes, new testids.

CEO Demo Script

1. Search a word with 3+ hits; open the thread.
2. All hits show a faint highlight; exactly one is boldly marked.
3. Click ▼ repeatedly — the bold mark hops match to match as the counter
   climbs; you always know where the loop is.
