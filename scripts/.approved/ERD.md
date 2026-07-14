ERD — testchat M17: Loadable-Memory Counter (erd_version 32)

What changes v31 -> v32

Two edits: status.py computes and returns loadable_gb; app.js renders it in
the status strip. Additive — every existing field and behavior stays.

File inventory (M17 build) — DAG order

1. src/api/status.py — EDIT. Add one helper and one payload field:
   - New function _loadable_gb() -> float. Design (the formula IS the
     spec, AC-61): parse the existing vm_stat output for these page
     counts: "free", "speculative", "purgeable", "File-backed pages",
     "wired down". reclaimable_gb = (free + speculative + purgeable +
     file-backed) * page_size / 1024**3. Read the GPU wired cap via
     `sysctl -n iogpu.wired_limit_mb` (2s timeout, same subprocess style
     as the existing helpers): if it yields a positive integer, cap_gb =
     that value / 1024; otherwise cap_gb = 0.75 * total_gb. gpu_headroom_gb
     = cap_gb - wired_gb. Result: max(0.0, min(reclaimable_gb,
     gpu_headroom_gb) - 4.0) — the 4 GB is a safety margin. Every failure
     path returns 0.0 and logs via logger.exception, matching the file's
     existing error style.
   - get_status() gains "loadable_gb": round(<the helper>, 1). All
     existing fields unchanged.
   - Reuse the existing vm_stat/sysctl subprocess patterns already in this
     file; total_gb comes from the existing hw.memsize read.

2. src/static/app.js — EDIT. In the status-strip poll handler (the code
   that builds the 'RAM X/Y GB' string around the statusRam element):
   when d.loadable_gb is a number, append " · ~" + d.loadable_gb +
   " GB loadable" to the existing text. Nothing else in the file changes.

Contract ids per task: contracts = [] — an EMPTY list, for BOTH tasks.
NEVER invent module-style ids.

Task dependencies: the src/static/app.js task MUST list the status.py task
in its depends_on (final task).

Oracle Mapping: the new/updated API node-ids in tests/test_status_api.py
map to the src/api/status.py task. ALL browser node-ids are carried
forward — do NOT map them (the shell auto-assigns regression; D-57/D-64).

Test dependencies: none new.
