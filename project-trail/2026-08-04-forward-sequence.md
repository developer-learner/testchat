# Forward sequence — pipeline reliability work (2026-08-04)

Sequenced next steps out of the EM-context/reliability session. Dependencies are
real (stated per phase), not preferences. Full evidence + design:
`project-trail/2026-08-04-em-context-scoping-proposal.md`.

**First line for the next pass:** nothing moves until Phase 0 is settled.

## Phase 0 — Housekeeping (one decision, ~0 effort)
- Decide `tasks/CURRENT.md` (modified at session start, not this work's; excluded
  from all 7 session commits). Commit / revert / leave. Tree is then fully clean.

## Phase 1 — Close the gap (precondition for everything below)
- Port the closure-repair synthetic gate into `scripts/selftest/selftest_gates.py`
  (subprocess-fixture style, CI-run, manifest-pinned — NOT `tests/`, the frozen
  INV-1 app suite). 7 cases listed in the proposal doc's Status block.
- **Why first:** makes the closure auto-repair (commit `f757bb4`) *enforceable*, and
  the tests must travel with the code on backport.

## Phase 2 — Propagate (your go; before Phase 3, not after)
- Backport to blueprint → children: Wave 1 (task-key skeleton), validator
  key-naming message, closure auto-repair — **code + tests together**.
- **Why now:** every later testchat change grows the backlog; Phase 1 is warm.
- **Conscious call:** this is backport-**before**-live-confirm. Acceptable because
  the risk is architecturally contained — `validate()` untouched (worst case in any
  child is "fails to repair" = today, never passes a bad plan), and the orchestrate
  call is `… || true` (a repair crash is swallowed; `validate()` runs on the
  un-repaired plan). Belt-and-suspenders option: gate this on the first
  `closure-repair:` line in a real testchat run (Standing watch). Both defensible.

## Phase 3 — The next lever (Wave-1-shaped, measure-first)
- id-format / never-invent-contract-id **verbatim rules** — the 5/32 id subtype.
  Same replay harness + measure-first gate as Wave 1. Cheap.
- **Also shrinks the Phase-5 population** — the recurring rule is the retry generator.

## Phase 4 — Measure, then decide (don't build blind)
- Re-measure the identical-retry population AFTER Phase 3. If the rules killed it →
  close the retry short-circuit as evidence-ruled-out. If it survives → build it.
- Suspicion: Phase 3 eliminates this. Verify before spending.

## Phase 5 — The big one (own session, own harness)
- Spec-tier quality — TPM-tier, root of the 60–90-min refreeze storms (M31: 5-for-5
  spec defects). Separate scoped pass with pre/post numbers like Wave 1.
- **Last, deliberately:** least-bounded item; Phases 3–4 clean up the counterfactual
  first. Deserves the discipline, not a bundled sprint.

## Standing — parallel, not sequential
- **Live-confirmation watch:** the first real closure-violating milestone must
  auto-pass — a `closure-repair:` line in the orchestrate log instead of an
  EM bounce. Constraint: **Phase 1 must land before the next milestone**, so that
  when the repair fires, CI is already enforcing it — the moment "proven" flips to
  "enforced" (Rule 6).

## Closed — do NOT re-open (evidence-ruled-out this session)
- ✗ Wave 2 file-count widening — EM is load-bearing; skip-population = 3 storm
  milestones. ✗ Wave 3 ERD trim — marginal (~3–8% prefill). ✗ Browser-test xdist —
  blocked (fixed ports 8971/8972 + shared server/storage + serial reset); the
  backend-concurrent lane (~40s, needs ≥2 CPUs) is the only small survivor.
