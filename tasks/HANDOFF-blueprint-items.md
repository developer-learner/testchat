# HANDOFF — sw-dev-blueprint items surfaced during testchat M28 close-out

date: 2026-07-19
status: parked — belongs in the blueprint repo, not testchat. Move this file when the blueprint work is picked up.

## Item 1: D-77 candidate — retry-in-isolation before declaring DRIFT

**Symptom (observed in testchat M28, spec v54):**
`scripts/orchestrate.sh` halted with SPEC DRIFT on
`tests/test_ui.py::test_thinking_placeholder_shows_then_clears` — a timing-sensitive M9-era Playwright test unrelated to the M28 delta (catalog UI / eject / modals). The same test:
- passed 150/150 in one earlier full-suite run in the same session
- passed 1/1 in isolation (`sandbox-run.sh -- pytest <nodeid>`)
- failed intermittently in subsequent full-suite runs at the same node-id

Every M28 task's own projection passed. The delta's inventory (`contracts.files`) did NOT include the file exercised by the failing test — it was a carried-forward regression node. So drift detection triggered on a flake, not real drift, and the CEO manually authorized `[success]` (testchat commit `69708e4`) after documenting the process guard (isolate + inventory-check + CEO consent, testchat correction log 2026-07-19).

**Proposed fix (blueprint side, `scripts/orchestrate.sh`):**
Before declaring DRIFT and packaging the escalation, re-run any failing node-id in isolation N times (say N=2). If the isolated run passes AND the failing test's file is outside the delta's `contracts.files` inventory, log a WARNING and treat as flake (not drift). If it reproduces in isolation, or is inside the delta inventory, proceed with DRIFT as today.

**Grounding (existing precedent):**
- D-58 determinism gate — this class of "same suite, different outcome" already has repo-level plumbing.
- D-57 auto-regression bookkeeping — the shell already knows which nodes are carried-forward vs delta-mapped; the check is just "is this file in `contracts.files`?"
- Rule 6 corollary (CLAUDE.md): "'nothing went wrong' ≠ 'safeguard works'" — currently the reverse also holds: "something went wrong" ≠ "safeguard tripped for the right reason". The flake path proves the second half.

**Scope estimate:** ~30-50 lines in `orchestrate.sh` around the DRIFT branch, one new DECISIONS.md entry (D-77), possible selftest to lock the behavior.

**After the blueprint fix ships:** `update-template.sh --dry-run` in testchat → `--approve <sha>` → the retry gate lands automatically.

---

## Item 2: Stray `.bak` file in blueprint tasks/

**Path:** `sw-dev-blueprint/tasks/HANDOFF-2026-07-16-state.md.bak`
**Timestamps:** the `.bak` is dated Jul 17 19:04; the tracked-name-alike `HANDOFF-2026-07-16-state.md` (also untracked per `0622ec1 chore(tasks): untrack dated session-state handoffs`) is dated Jul 17 19:28.
**Status:** untracked; appears to be an editor backup made before an edit ~24 minutes later. Both the `.md` and `.bak` are excluded from the frozen manifest by the untrack commit, so nothing depends on it.

**Recommended action:** `rm sw-dev-blueprint/tasks/HANDOFF-2026-07-16-state.md.bak`. It's noise in `git status`.

**Optional:** add `*.bak` to blueprint's `.gitignore` so future editor backups don't accumulate as untracked cruft.

---

## Not-pending in testchat itself

The flake documentation lives in testchat's [CLAUDE.md](../CLAUDE.md) correction log (2026-07-19 row) with the process guard. That's all testchat can do — the test file is TPM-frozen (INV-1) and the mechanical fix belongs upstream in blueprint.
