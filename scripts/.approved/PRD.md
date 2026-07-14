PRD — testchat M22: Count Only Visible Search Hits

Milestone

CEO demo found the search-hit navigation useless in real threads: matches
inside the COLLAPSED thinking section of assistant replies are hidden text,
but M19's highlighter counts them — in a real thread 75 of 82 hits were
invisible, so the counter over-reports and the arrows mostly point at
matches the CEO cannot see. M22: only visible matches participate in the
count and navigation.

Acceptance Criteria

- AC-74: WHEN search hits are collected for the counter and navigation,
  hits with no rendered geometry (hidden content, e.g. collapsed thinking
  sections) SHALL be excluded; the counter total SHALL equal the number of
  visible highlights, and the arrows SHALL cycle only through those.
- All prior ACs unchanged.

Out of Scope: re-counting when the thinking toggle changes visibility
mid-thread (re-rendering already refreshes hits on the next search/thread
action), highlighting behavior inside hidden regions (harmless).

CEO Demo Script

1. Search a common word ("the"); open a thread whose reply has a thinking
   section.
2. The counter now shows a small, honest number (only what you can see).
3. ▼ hops the bold mark visibly match to match — every click moves it.
