ERD — testchat M11a: Phosphor Theme (erd_version 22)

What changes v21 → v22

One new small file (the rain backdrop) and three edits. Cut per D-60: one
concern per task. The theme system already exists (data-theme attribute on
<html>, CSS variable blocks per theme, THEMES array + icon map in app.js,
localStorage persistence) — phosphor plugs into it; nothing is redesigned.

File inventory (M11a build) — DAG order

1. src/static/rain.js — NEW (~70 lines, no dependencies, plain script like
   app.js — an IIFE exposing window.MatrixRain = { start: fn, stop: fn }).
   start(): create (once) a full-viewport <canvas> as document.body's first
   child with data-testid="matrix-rain", position fixed, inset 0,
   z-index 0, pointer-events none, opacity 0.35; run the classic digital
   rain: columns ~14px wide, each drawing a random glyph from katakana +
   digits (e.g. charcodes 0x30A0-0x30FF plus 0-9) falling one row per
   frame-step, head brighter than tail, fading via a translucent black
   fillRect each frame; colors from the phosphor palette (head
   'rgb(190,255,200)', trail 'rgb(60,220,120)'); throttle to ~20 fps via
   requestAnimationFrame + timestamp check; pause when document.hidden
   (visibilitychange); handle window resize. If
   matchMedia('(prefers-reduced-motion: reduce)').matches, draw ONE static
   frame and do not animate. stop(): cancel the animation and hide the
   canvas (display none) — do not destroy it.
2. src/static/style.css — EDIT (one concern: the phosphor theme block).
   Append a [data-theme="phosphor"] variable block mapping the EXISTING
   theme variable names (copy the set the matrix block defines) to the
   spec tokens: background oklch(0.16 0.02 155); foreground/text
   oklch(0.9 0.16 150); primary/accent-strong oklch(0.82 0.24 148) with a
   dark green contrast foreground; secondary accent oklch(0.75 0.19 165);
   cards/surfaces slightly lifted dark green-black (e.g.
   oklch(0.20 0.025 155)); borders 18%-alpha primary, inputs 12%, focus
   ring 60% (color-mix or oklch alpha); border radius overridden to
   0.25rem; font-family for the whole app under this theme: ui-monospace,
   SFMono-Regular, Menlo, Consolas, monospace. Also under
   [data-theme="phosphor"] only: a .matrix-scanlines overlay on the chat
   panel via a repeating-linear-gradient ::before (2px period, very low
   alpha, pointer-events none); text glow on assistant text and headers
   (text-shadow 0 0 6px currentColor at low alpha); .box-glow on the
   terminal-ish containers (subtle green ring + outer glow); make the app
   chrome sit above the rain canvas (the app wrapper gets position
   relative / z-index 1 — do this in a theme-neutral way if not already
   true). Touch NOTHING outside the appended block plus, if needed, that
   one z-index rule.
3. src/static/index.html — EDIT (one concern): add
   <script src="/static/rain.js"></script> BEFORE the app.js script tag.
4. src/static/app.js — EDIT (LAST, depends on all; one concern): register
   the theme. In the THEMES array add 'phosphor' (after 'matrix'); add its
   toggle icon mapping (a text glyph, e.g. '𐌘' or '>_' — any non-emoji
   marker consistent with THEME_ICONS' type); in applyTheme(), after
   setting the attribute: if theme === 'phosphor' call
   window.MatrixRain.start(), else window.MatrixRain.stop() (guard with
   typeof window.MatrixRain !== 'undefined' so app.js never breaks if
   rain.js failed to load).

Constraints

All prior constraints carry forward. New:
C-24: no network-loaded assets — fonts come from the system monospace
stack; glyphs are drawn, not fetched.
C-25: the rain must never intercept input (pointer-events none, z-index
below the app chrome) and must not run while another theme is active or
the tab is hidden.

Contract ids per task: ALL FOUR tasks use contracts = [] except none —
frontend files: always an empty list; never invent module-style ids.

Oracle Mapping (AC → test node) — guidance for the plan

- ALL browser node-ids (tests/test_ui.py::*, 18 after this freeze) → the
  FINAL task (src/static/app.js), which depends_on the other three.
- rain.js, style.css, index.html tasks carry NO mapped tests — their
  acceptance is their contracts.smoke_checks entries.
- No backend node-ids change ownership; the shell carries the rest (D-57).

AC-53 → tests/test_ui.py::test_theme_cycle_reaches_phosphor_and_wraps
AC-54 → tests/test_ui.py::test_rain_backdrop_only_in_phosphor

Test dependencies

No new dependencies.
