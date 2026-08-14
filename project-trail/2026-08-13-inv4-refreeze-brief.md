# 2026-08-13 — INV-4 refreeze handoff (settings-status)

Deferred per CEO ruling ("merge after T9, refreeze for INV-4") from the
8-finding review remediation batch. This is the self-contained brief for
the TPM refreeze lane — no re-triage required.

## The invariant violation

- **File:** `tests/test_ui_settings.py:22-23` — the test locates testid
  `settings-status`.
- **Contract check:** `scripts/check-test-surface.py` (INV-4: tests ⊆
  locked surface) — `settings-status` does not exist in `contracts.ui`.
- **Origin:** pre-existing, introduced host-side at `7bfc622`
  (2026-08-09, direct lane). Confirmed during T6 verification; NOT edited
  during the batch by design.

## Why it matters

INV-4 is the structural guarantee that tests can only observe the locked
boundary. A testid outside `contracts.ui` is silent drift: the test still
runs, so nothing trips, but the surface contract and the test disagree.
It is exactly the class this invariant exists to catch; it was missed at
freeze time because the host-side commit bypassed the TPM path
(CEO-authorized direct-edit precedent `7bfc622`/`f569528`).

## What the refreeze should do

Either (a) add `settings-status` to `contracts.ui` in the next TPM
refreeze delta (the testid is behaviorally legitimate — it pins the
settings status indicator), or (b) re-point the test at an existing
contract testid if `settings-status` is redundant with a shipped id.
Choice is the TPM's seat; the delta must carry the AC or contract line
that justifies it.

## Verification after the fix

1. `python3 scripts/check-test-surface.py` — clean.
2. Target test run:
   `PYTHONPATH=. python3 -m pytest tests/test_ui_settings.py -q -p no:cacheprovider`
3. Full suite green (212 tests, host serial ~5-6 min or `-n auto` under
   pytest-xdist once item C lands: ~1.5 min).