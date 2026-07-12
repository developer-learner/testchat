ERD — testchat M11a: Phosphor Theme (erd_version 23)

What changes v21 → v22

One new small file (the rain backdrop) and three edits. Cut per D-60: one
concern per task. The theme system already exists (data-theme attribute on
<html>, CSS variable blocks per theme, THEMES array + icon map in app.js,
localStorage persistence) — phosphor plugs into it; nothing is redesigned.

File inventory (M11a build) — DAG order

1. src/static/rain.js — NEW (~70 lines). Every decision is made below;
   TRANSCRIBE this skeleton into working JavaScript, no analysis:

   (function () {
     var canvas = null, ctx = null, raf = null, last = 0, drops = [];
     var FONT = 14, STEP_MS = 50;
     var GLYPHS = katakana 0x30A0..0x30FF plus digits 0-9, as one string
       built with String.fromCharCode in a small loop;
     function ensureCanvas():
       if canvas already created -> return; create <canvas>, set
       data-testid="matrix-rain", style: position fixed, inset 0,
       zIndex 0, pointerEvents 'none', opacity 0.35; insert as
       document.body.firstChild; ctx = getContext('2d'); call resize();
       window.addEventListener('resize', resize);
       document.addEventListener('visibilitychange', function(){ /* raf
         loop simply does nothing while document.hidden */ });
     function resize(): canvas.width/height = innerWidth/innerHeight;
       drops = new Array(Math.ceil(canvas.width / FONT)).fill(0).map(
         function(){ return Math.floor(Math.random() * canvas.height / FONT); });
     function frame(ts):
       raf = requestAnimationFrame(frame);
       if (document.hidden) return;
       if (ts - last < STEP_MS) return; last = ts;
       ctx.fillStyle = 'rgba(0,0,0,0.08)';
       ctx.fillRect(0,0,canvas.width,canvas.height);
       ctx.font = FONT + 'px monospace';
       for each column i in drops:
         var ch = random glyph from GLYPHS;
         var x = i * FONT, y = drops[i] * FONT;
         ctx.fillStyle = 'rgb(60,220,120)'; ctx.fillText(ch, x, y);
         ctx.fillStyle = 'rgb(190,255,200)'; ctx.fillText(ch, x, y); //head brighter: draw same glyph once more at lower alpha via globalAlpha 0.9, then restore globalAlpha 1
         drops[i] = (y > canvas.height && Math.random() > 0.975) ? 0 : drops[i] + 1;
     function start():
       ensureCanvas(); canvas.style.display = 'block';
       if (matchMedia('(prefers-reduced-motion: reduce)').matches)
         { draw ONE frame by calling the frame body once without
           scheduling; return; }
       if (!raf) { last = 0; raf = requestAnimationFrame(frame); }
     function stop():
       if (raf) { cancelAnimationFrame(raf); raf = null; }
       if (canvas) canvas.style.display = 'none';
     window.MatrixRain = { start: start, stop: stop };
   })();

   Anything the skeleton leaves as prose (e.g. the head-brightness line),
   resolve in the simplest way that satisfies it — do not add features.

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
