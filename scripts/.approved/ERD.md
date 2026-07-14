ERD — testchat M21: Distinct Current-Hit Emphasis (erd_version 39)

What changes v37 -> v38

One file: style.css. The two search-hit rules are re-specified for
contrast; nothing else moves.

File inventory (M21 build) — DAG order

1. src/static/style.css — NO EDIT NEEDED (declared in contracts.no_edit_files, D-65): the repair and the contrast rules below already landed as a CEO-session live-fix after three coder strikes; this freeze ratifies them. Original edit spec, now describing the existing state: Replace the bodies of the two existing
   search-hit rules:
   a) mark.search-hit: background var(--toggle-on-bg), color inherit,
      border-radius 3px, padding 0 2px.
   b) mark.search-hit.current: background var(--accent), color
      var(--accent-contrast), border-radius 3px, padding 0 2px,
      outline 2px solid var(--accent-hover).
   The selectors stay exactly as they are; only their declarations change.
   Nothing else in the file changes.

Contract ids per task: contracts = [] — an EMPTY list. NEVER invent
module-style ids.

Oracle Mapping: no new node-ids. ALL browser node-ids are carried
forward — do NOT map them (the shell auto-assigns regression, D-57).

Test dependencies: none new.
