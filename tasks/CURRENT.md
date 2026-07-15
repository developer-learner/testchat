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

**Open items:**
- CEO demo acceptances for M14–M22 (all in live use, none recorded)
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
