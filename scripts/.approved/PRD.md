PRD — testchat M10: Ratify the Sprint (freeze coverage for the live-fix features)

Milestone

M11b adds a fifth theme, "midnight" — designed for a dark room lit only by
the laptop: maximal readability with zero theater. Very dark neutral grey
(not pure black — avoids halation), warm off-white text (not pure white —
avoids glare), hierarchy by lightness steps, muted amber for interactive
elements, desaturated cyan-slate as the secondary accent, hairline chrome,
and explicitly NO glow, scanlines, or rain. Existing themes untouched.

All v24 criteria remain in force, with one amendment: the theme cycle now
contains FIVE themes (the AC-53 test updates accordingly).

AC-55: WHEN the user cycles the theme toggle, THE SYSTEM SHALL reach a
"midnight" theme, and a full five-click cycle SHALL return to the start.

manual-only waivers (D-58): midnight's colors, contrast feel, and
readability-in-the-dark are design — verified by the CEO in an actual dark
room, which no headless browser can simulate.

Out of Scope: layout changes (the phosphor terminal-window treatment is
M11c); any behavior change.

CEO Demo Script: lights off. Cycle to midnight — screen goes quiet: dark
grey, soft warm text, amber only where you can click. Read a long reply —
no glare, no smear. Reload — still midnight.
