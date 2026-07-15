# CURRENT.md — Session Notes

> Human-facing status page, NOT the spec. Frozen spec lives in
> scripts/.approved/ and changes only via scripts/refreeze.sh (D-31).

---

## State at 2026-07-14 session end (handoff)

**Frozen spec:** v40, `[success]` tagged, 108/108 green, pushed to
GitHub (origin = developer-learner/testchat, current as of this session).

**Shipped this sprint (M14–M22, v28–v40):** rain-on-matrix ratify, phosphor
terminal window, newest-thread-first sidebar, loadable-RAM counter
(status strip; predicts whether a model load will fit), thread search +
in-thread highlighting + hit counter with prev/next navigation +
visible-only hit counting (collapsed think-text excluded).

**Models:** `qwen/qwen3.6-27b` holds BOTH EM and coder seats — mapping
verified in the VM copy of models.env (the copy the pipeline reads; the
host copy is reference-only). 35B retired. An `unsloth/qwen3.6-27b-mlx`
variant was benched head-to-head: no quality difference, slightly slower,
+5 GB — recommend unloading/deleting it. EM-seat production validation:
1 clean run (M21 plan); call it settled after ~3.

**M14–M22 CEO-ACCEPTED (2026-07-14):** all nine demoed live in the browser
and formally accepted, no exceptions. Verification evidence: rain renders in
matrix only and terminal titlebar in phosphor only (all 10 themes cycled);
new chat lands at top of sidebar; RAM counter live in status strip; "pebble"
search filtered 26 threads to the 2 containing it; hit counter/nav honest
(thread had 11 raw matches, 6 in collapsed think-sections, counter said 5 —
AC-74 measured in the DOM); current-hit loud vs other-hits subtle confirmed
in one frame. Themes additionally eyeballed by the CEO directly.

**CI GREEN (2026-07-14/15) — first fully green CI in project history.**
Chronicle: the audit round found bare `mypy src/` dying on duplicate module
basenames before checking anything (CI had been dark for the repo's whole
unpushed life). Fix chain: `--explicit-package-bases` → test step had never
run either (no PYTHONPATH, no chromium, no .cache dir) → models.py:37
arg-type live-fix (the one true mypy finding; CEO-authorized `0bbcfce`) →
coverage bar 80→75 (CEO-approved: Linux measures 78, macOS 83 —
status.py's RAM paths are mac-only; ratchet up at M23). Latest main
(template-update 883bf99, D-69) passed a fresh CI run first-try.

**Flake record for the next TPM cycle:** one slow CI run (32s suite vs
usual 19s) flaked two UI tests, both green on rerun and on the next fresh
run: `test_thinking_placeholder_shows_then_clears` (inherent observation
race — the test must attach within the stub's ~1.2s hold window) and
`test_sidebar_lists_newest_thread_first` (one-off count mismatch, likely a
late persist PUT from the prior test). Zero-retry law governs the sandbox
oracle; CI is a second, noisier environment. Harden both at the M23
refreeze.

**Open items:**
- M23 candidate "honest saves": persist-failure indicator (threads.js:25 —
  now flagged by the D-68 gate), tighten threads role to Literal, drop the
  7 unused frozen-test imports, harden the two flake-record UI tests,
  ratchet CI coverage bar back up
- Product roadmap (CEO's pick): mobile layout, export/import, multi-model
  comparison
- Blueprint packaging: cheap-tier publish idea (honest README, repo
  public as-is) discussed, no decision
- Escalation-ladder validation run (template backlog, needs a milestone
  run with MAX_TASK_STRIKES=2)

**Conduct notes for the next conductor:** verify state from the tree, not
from memory or summaries (this session's worst errors were stale-claim
errors); give the CEO a time estimate before every pipeline run and report
the first halt immediately; view user-visible milestones in a real browser
before presenting; the CEO gets plain-language claims, never diffs.

## Results

Full frozen TPM suite green against spec v44. Feature built and validated.
