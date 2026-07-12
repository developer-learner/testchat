ERD — testchat M11b: Midnight Theme (erd_version 25)

What changes v24 → v25

Two edit-mode tasks, one concern each. The theme system is untouched
mechanically; midnight is a fifth entry.

File inventory (M11b build) — DAG order

1. src/static/style.css — EDIT: append a [data-theme="midnight"] variable
   block defining the SAME variable-name set the phosphor block defines
   (copy its list of names), with these values:
   --font: unchanged from the app default (do NOT force monospace);
   --bg: oklch(0.18 0 0);            /* dark neutral grey, not black */
   --panel: oklch(0.22 0.003 90);    /* assistant surfaces: one step up */
   --text: oklch(0.92 0.01 90);      /* warm off-white */
   --border: oklch(0.92 0.01 90 / 0.08);  /* hairline */
   sidebar set: bg oklch(0.16 0 0), text oklch(0.85 0.01 90), border 8%
   alpha, hover oklch(0.22 0 0), active oklch(0.26 0.003 90),
   active-bar oklch(0.75 0.12 75);
   interactive/accents (whatever accent variables the other theme blocks
   define): primary amber oklch(0.75 0.12 75) with dark foreground; a
   secondary desaturated cyan-slate oklch(0.72 0.06 220) for the user
   bubble tint; error a dim red oklch(0.55 0.12 25).
   User bubbles: a slightly lighter cyan-tinted step, NOT saturated.
   Explicitly under midnight: text-shadow: none on any element other
   theme blocks give glow to. No ::before overlays. Nothing else changes.
2. src/static/app.js — EDIT (LAST, depends on 1): add 'midnight' to the
   THEMES array after 'phosphor' and give it an icon in the icon map
   (moon emoji or a dot glyph, matching the map's existing style).
   Nothing else changes — MatrixRain remains phosphor-only by the
   existing applyTheme logic.

Contract ids per task: contracts = [] for both (frontend files — never
invent module-style ids).

Oracle Mapping — guidance for the plan

- ALL browser node-ids (tests/test_ui.py::*, 18) → the FINAL task
  (src/static/app.js), depends_on the style.css task.
- style.css task: no mapped tests; acceptance = its smoke_check.
- The updated cycle test (five themes) and AC-55 ride the same node-ids.

Test dependencies: none new.
