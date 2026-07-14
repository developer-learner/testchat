PRD — testchat M18: Thread Search

Milestone

The sidebar has grown past easy scanning. M18 adds a search box above the
thread list: type text and the list filters, live, to threads whose title
or message content contains it; clear the box and the full list returns.
Plain case-insensitive text matching, entirely in the browser — no AI, no
external service, no backend change.

Acceptance Criteria

- AC-63: WHEN text is entered in the sidebar search box, the thread list
  SHALL show only threads whose title or any message content contains that
  text, case-insensitively.
- AC-64: WHEN the search box is emptied, the thread list SHALL show all
  threads again, in the existing newest-first order.
- AC-65: WHILE a filter is active, thread ordering among matches SHALL
  remain newest-first, and clicking a match SHALL open it exactly as an
  unfiltered click does.

Out of Scope: semantic/AI search, result highlighting, ranking, backend
search endpoints, searching across deleted threads.

CEO Demo Script

1. Open the app — a search box sits above the thread list.
2. Type a word you remember from an old chat — the list shrinks to the
   threads containing it, as you type.
3. Click a result — the thread opens normally.
4. Clear the box — the full list is back, newest on top.
