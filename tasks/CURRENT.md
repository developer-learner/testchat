# CURRENT.md — Session Notes

> Human-facing status page, NOT the spec. Frozen spec lives in
> scripts/.approved/ and changes only via scripts/refreeze.sh (D-31).

---

## State at 2026-07-15 session end (handoff)

**Frozen spec:** v45 (M24 "History Never Dies", frozen 2026-07-15,
`9050b24`; 117 frozen tests — oracle proof: 7 new fail-on-current,
117/117 pass-on-intended). Prior: v44 `[success]` tagged, CEO-accepted,
pushed to GitHub (origin = developer-learner/testchat), feature-complete
by CEO decision — M24 is the one PM-audit data-safety hole (silent
corrupt-history destruction) plus the AC-83 hover-timestamp ratify.

**Shipped this sprint (M14–M23, v28–v44):** rain-on-matrix ratify, phosphor
terminal window, newest-thread-first sidebar, loadable-RAM counter
(status strip; predicts whether a model load will fit), thread search +
in-thread highlighting + hit counter with prev/next navigation +
visible-only hit counting (collapsed think-text excluded), M23 honest saves
(persist-failure indicator, threads role Literal 422, lint cleanup, flake
hardening). Escalation ladder armed (D-70) and validated — every rung fired.

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
- Coverage ratchet: CI measures the 111-test suite; ratchet bar back up
  from 75 once Linux/macOS gap narrows
- EM diagnosis hardening: schema-retry or dense-diagnosis brief as template
  candidate (M23 exposed mid-tier diagnosis as the weak rung)
- Blueprint packaging: cheap-tier publish idea (honest README, repo
  public as-is) discussed, no decision
- LM Studio housekeeping: delete `unsloth/qwen3.6-27b-mlx` (+5 GB, benched
  strictly worse)

**Conduct notes for the next conductor:** verify state from the tree, not
from memory or summaries (this session's worst errors were stale-claim
errors); give the CEO a time estimate before every pipeline run and report
the first halt immediately; view user-visible milestones in a real browser
before presenting; the CEO gets plain-language claims, never diffs.

## Results

Full frozen TPM suite green against spec v44. Feature built and validated.

**M23 HONEST SAVES COMPLETE: `[success] spec v44` (`d9c17cb`), 111 frozen
tests, final subtree run 72s.** First milestone with: MTPLX serving both
seats (host.lima.internal:8000, drift-immune), MAX_TASK_STRIKES=2, and a
frontier conductor doubling as TPM (D-39). Browser-eyes verified live:
"not saved" appears when the backend dies mid-session, clears on recovery;
invalid-role PUT returns 422.

**Escalation-ladder validation (the run's second purpose) — VERDICT: every
rung fired, one EM weakness found.** Retry-with-evidence fired (T7 strike
1→2); EM consult fired; the diagnosis came back schema-invalid
(empty task_id) and the gate refused it — halting correctly. Data point
for D-66: the MTPLX 27b plans cleanly (3rd plan valid) but stumbled on
diagnosis, matching the historical mid-tier pattern. Ladder is no longer
dead code.

**Cost ledger, honest: 4 freezes (v41→v44), ALL THREE spec bugs the
TPM's (this conductor's):** (1) no_edit_files declared without smoke
checks — unsatisfiable EM puzzle, M8 class; (2) D-64 dependency edges
asserted in prose but never instructed — the EM transcribes, it doesn't
invent; (3) the new UI test miscounted replies (two sends in ONE thread
need count=2 in _await_reply — every prior two-send test used fresh
threads). The coder was blameless: T7 attempt 1 was character-identical
to the ERD prescription and burned two strikes on the TPM's test bug.
TPM lesson encoded: state DAG edges explicitly; walk helper defaults
before freezing a test; a no-edit declaration still needs an acceptance
signal. Gates D-65 (4 no-op tasks skipped coder), D-67 (lint gate green
at every freeze), D-68 (clean output passed) all did production duty.

Residue: three empty "New Chat" threads created during browser
verification/demo — CEO deletes by hand at leisure (scripted delete
clicks no-op; real gestures work).

**M23 CEO-ACCEPTED (2026-07-15).** Demoed live to the CEO: backend killed
under an open page → "not saved" in the status strip; backend restored +
save retried → warning cleared, RAM counter back. Claim accepted: "if a
save ever fails the app says so immediately, clears on recovery; frozen
test #111 re-verifies forever." No exceptions.

## Results

Full frozen TPM suite green against spec v45. Feature built and validated.
