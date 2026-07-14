ERD — testchat M15: Phosphor Terminal Window (erd_version 30)

What changes v28 -> v29

Two small edits: index.html gains the terminal title-bar markup (always in
the DOM); style.css gains the phosphor-only window treatment. No JS changes.

File inventory (M15 build) — DAG order

1. src/static/index.html — EDIT. Inside <main class="chat-panel">, as its
   FIRST child, add one div: class "terminal-titlebar", attribute
   data-testid="terminal-titlebar". Inside it, in order: three empty <span>
   elements each with class "tl-dot", then one <span class="tl-title"> with
   the text: testchat — local session. Nothing else changes in the file.

2. src/static/style.css — EDIT (two tightly-related additions, both inside
   the theme area of the file, near the existing phosphor rules):
   a) Base rule (applies to all themes): ".terminal-titlebar { display: none; }"
      — the chrome is invisible everywhere by default.
   b) Phosphor-only rules under the :root[data-theme="phosphor"] scope:
      - .terminal-titlebar becomes a flex row (display: flex; align-items:
        center; gap ~0.5rem; padding ~0.5rem 0.9rem), background slightly
        darker than the panel (use the theme's oklch greens, e.g.
        oklch(0.12 0.02 155)), border-bottom 1px using the phosphor
        --border color.
      - .tl-dot: 12px circle (border-radius 50%). First dot red-ish
        (oklch(0.65 0.2 25)), second amber (oklch(0.8 0.16 85)), third
        green (oklch(0.75 0.2 145)) via :nth-child(1|2|3).
      - .tl-title: small monospace text (~0.75rem) in the theme's muted
        green (--muted-text), letter-spacing ~0.05em.
      - .chat-panel window framing: margin ~1.25rem (inset from edges),
        border 1px solid the phosphor --border color, border-radius
        ~10px, overflow hidden (so the title bar's corners clip), and a
        soft outer glow box-shadow (e.g. 0 0 24px
        oklch(0.82 0.24 148 / 0.10)).

Contract ids per task: contracts = [] — an EMPTY list, for BOTH tasks.
Frontend files have no module entry points; NEVER invent module-style ids.

Oracle Mapping: ALL browser node-ids (including the new
tests/test_ui.py::test_terminal_titlebar_only_in_phosphor) map to
src/static/app.js (final in DAG), exactly as in every prior milestone. All
non-browser node-ids stay mapped as in v28. Every file in the inventory carries a smoke_check as its per-task signal.

Test dependencies: none new.
