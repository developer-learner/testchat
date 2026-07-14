PRD — testchat M16: Newest Thread First

Milestone

M16 flips the sidebar thread list to newest-first. Today the list renders in
creation order, so the newest chat lands at the bottom — the CEO has to
scroll past every old thread to find the conversation just started. Standard
chat UX puts the newest thread on top; this milestone makes the sidebar do
that. Storage order and persistence are untouched — only the rendered order
changes.

Acceptance Criteria

- AC-59: WHEN the sidebar renders, threads SHALL be listed newest-first
  (reverse creation order); a newly created thread SHALL appear at the top.
- Prior ACs touching sidebar positions (AC-29, AC-31, AC-41) are amended in
  their tests to address the original thread at its new position; their
  behavior claims (history restore, model lock, message retention) are
  unchanged.

Out of Scope: sorting by last activity (creation order only, reversed),
drag-to-reorder, pinning, any storage/persistence change.

CEO Demo Script

1. Open the app — existing threads now list newest on top.
2. Click "+ New Chat", send a message — the new thread sits at the TOP of
   the sidebar, titled from your message.
3. Click an older thread lower down — history loads exactly as before.
4. Reload — order survives, newest still on top.
