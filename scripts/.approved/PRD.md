PRD — testchat M19: Search-Hit Highlighting

Milestone

M18's search finds the right threads, but opening one gives no clue WHERE
the match is — the CEO reported exactly this. M19: while a search is
active, every occurrence of the search text inside the opened thread's
messages is visually highlighted, and the view scrolls to the first hit.
Clearing the search removes all highlights.

Acceptance Criteria

- AC-66: WHEN a thread is opened (or re-rendered) WHILE the sidebar search
  box holds text, every case-insensitive occurrence of that text within the
  rendered message content SHALL be wrapped in a visible highlight element
  (locked testid: search-hit).
- AC-67: WHEN the search box is emptied, previously shown highlights SHALL
  disappear from the open thread.
- AC-68 (manual-only: smooth scrolling is animation, excluded from the
  frozen oracle by the D-58 determinism rules): WHEN highlights are
  applied, the first hit SHALL be scrolled into view. Verified in the CEO
  demo.

Out of Scope: highlighting inside the sidebar titles, next/previous-hit
navigation, match counts, regex or multi-word logic beyond the existing
plain-text match.

CEO Demo Script

1. Search a word you remember from an old chat; click a matching thread.
2. Every occurrence of the word in the conversation is highlighted, and
   the view has jumped to the first one.
3. Clear the search box — highlights vanish.
