PRD — testchat M20: Search-Hit Count and Navigation

Milestone

M19 highlights matches and jumps to the first, but gives no sense of HOW
MANY matches exist or a way to visit the rest — the CEO can't tell whether
to keep looking. M20 adds a hit counter ("2/7") and previous/next arrows
under the search box: the arrows cycle through the highlighted hits
(wrapping at the ends), scrolling each into view and marking the current
one distinctly.

Acceptance Criteria

- AC-69: WHEN a thread is open WHILE a search is active, a counter (locked
  testid: search-hit-count) SHALL show the current hit position and total
  as "K/N" (1-based); with no hits it SHALL show "0/0".
- AC-70: WHEN the next control (search-next-btn) is activated, the current
  selection SHALL advance to the following hit, wrapping from the last hit
  to the first; the previous control (search-prev-btn) SHALL do the same
  in reverse. The counter SHALL update accordingly.
- AC-71: WHEN the search box is emptied, the counter and controls SHALL be
  hidden.
- AC-72 (manual-only: scrolling and visual emphasis are appearance, D-58):
  the current hit SHALL be scrolled into view and visually distinct from
  the other hits. Verified in the CEO demo.

Out of Scope: cross-thread total counts in the sidebar, keyboard shortcuts
(Enter to cycle), match counts inside sidebar titles.

CEO Demo Script

1. Search a word with several occurrences; open a matching thread.
2. Under the search box: "1/N". Click ▼ — view jumps hit to hit, counter
   climbs, wraps back to 1 after N. ▲ goes backward.
3. Clear the search — counter and arrows disappear.
