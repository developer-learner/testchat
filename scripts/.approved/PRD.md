PRD — testchat M15: Phosphor Terminal Window

Milestone

M15 gives the phosphor theme the CEO's reference look (Vercel terminal-chat
screenshot): the chat panel reads as a floating terminal window — a title
bar with three window-control dots and a session title, a bordered, softly
glowing window frame, visually separated from the page behind it. Phosphor
already carries the scanlines, glow, and monospace type (M11a); this adds
the window chrome. All other themes are untouched — the chrome exists in
the DOM permanently but is visible only under phosphor.

Acceptance Criteria

- AC-56: WHEN the phosphor theme is active, the chat panel SHALL display a
  terminal title bar (locked testid: terminal-titlebar) containing three
  window-control dots and a static session title.
- AC-57: WHEN any theme other than phosphor is active, the terminal title
  bar SHALL be hidden.
- AC-58 (manual-only: window framing is appearance, not DOM state — the
  D-58 browser oracle cannot judge "looks like a floating terminal"): WHILE
  phosphor is active, the chat panel SHALL appear as a bordered, rounded,
  glow-shadowed window inset from the viewport edges. Verified in the CEO
  demo.

Out of Scope: rain (matrix-only since v28), sidebar restyling, new themes,
any behavior change to chat, threads, settings, or streaming.

CEO Demo Script

1. Cycle themes to phosphor (>_ icon).
2. Observe: chat panel is now a framed terminal window — title bar with
   three dots top-left, title text, rounded corners, green glow edge,
   visibly inset from the page background.
3. Send a message; confirm chat behaves exactly as before inside the frame.
4. Cycle to any other theme: chrome disappears, layout returns to full-bleed.
