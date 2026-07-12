PRD — testchat M10: Ratify the Sprint (freeze coverage for the live-fix features)

Milestone

M11a adds a fourth theme, "phosphor" — a Matrix-terminal look derived from a
CEO-supplied design spec: near-black green-tinted background, phosphor-green
text with glow, scanline overlay, sharp small radii, monospace type, and a
full-screen low-opacity digital-rain canvas behind the chat. The existing
light / dark / matrix themes are untouched; phosphor joins the toggle cycle.

All v21 acceptance criteria remain in force unchanged. New:

AC-53: WHEN the user cycles the theme toggle, THE SYSTEM SHALL reach a
"phosphor" theme, and a further full cycle SHALL return to the starting
theme (the cycle contains exactly four themes).

AC-54: WHILE the phosphor theme is active, THE SYSTEM SHALL display the
digital-rain backdrop; WHEN any other theme is active, THE SYSTEM SHALL
hide it.

manual-only waivers (D-58): the phosphor theme's exact colors, glow,
scanlines, flicker, rain density/glyphs — appearance is design (M10
precedent); AC-53/54 pin the mechanism. Reduced-motion behavior (static
backdrop when the OS requests reduced motion) — environment-dependent.

Out of Scope: terminal-style message labels (user@local / root@matrix) —
message-chrome behavior, separate decision. Fonts downloaded from the
network (system monospace stack instead). Any change to light/dark/matrix.

Flagged Assumptions: A19 phosphor is a NEW fourth theme, not a rework of
the existing matrix theme. A20 rain is canvas-based, created by rain.js,
capped opacity, paused when the tab is hidden, static under
prefers-reduced-motion.

CEO Demo Script: cycle themes to phosphor — green-on-black terminal look,
scanlines, glowing text, rain falling behind the chat; cycle away — rain
gone; reload on phosphor — still phosphor, rain running; chat normally —
everything readable.
