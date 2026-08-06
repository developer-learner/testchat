# Forward sequence — gate reliability & milestone speed (2026-08-06)

Handoff for a fresh thread. This is the *ordering* of the next passes, with
the dependency rationale each order holds for — not a flat backlog. The
session that produced it is documented in `2026-08-03-forward-plan.md`
(context-hygiene theory), the Wave 1/2 audits, and
`2026-08-04-em-context-scoping-proposal.md`.

## Where things stand (committed, tree clean except `tasks/CURRENT.md`)

- **Closure auto-repair shipped** (`f757bb4`): `validate-plan.py
  --repair-closures` — a best-effort pre-pass run by `ensure_plan` before the
  gate (scripts/orchestrate.sh:914, `|| true`) that adds the exact
  `depends_on` edge the D-64/import/route closure checks compute, only when
  the addition keeps the DAG acyclic. `validate()` UNCHANGED and runs after —
  safety is architectural: a repair bug can only fail to repair (= today),
  never pass a bad plan. ~10 of 32 archived plan-gate rejections (~31%)
  become deterministic no-LLM no-retry passes. Monotone: edges push tests
  later only.
- **Wave 1** (`d9f8536`): six task keys named verbatim in EM prompts; measured
  2/15 → 14/15 shape-valid on the production seat, length-halts flat.
- **Validator message** (`86e53f7`): subtree errors name the missing /
  unexpected keys.
- **Docs**: AC traceability audit, Wave 1 results + parallelization-claim
  correction, Wave 2 audit (file-count widening), closure-auto-repair record
  with ephemeral-gate finding (`0bfbfca`).

## The one known gap (recorded, next pass)

The synthetic gate that justified `f757bb4` (9 cases: add-edge / revert-cycle
/ no-op / self-dep + browser & import detection+repair) lived in a scratchpad
`test_repair_closures.py` and is NOT in the tree. "Proven" is not
"enforceable" until the suite is versioned (Rule 6). Import-closure cases
exist ONLY as constructed state (the violation requires the target file to be
absent from the tree — `not Path(t["file"]).exists()`, validate-plan.py:533),
so synthetic tests are the faithful reproduction, not a substitute for one.

## Sequenced plan

### Phase 0 — Housekeeping (one decision, ~0 effort)
1. **Decide `tasks/CURRENT.md`** — commit, revert, or leave; it was modified
   at session start, not ours, excluded from every commit. Nothing else moves
   until the tree is fully clean.

### Phase 1 — Close the gap (the next build, small)
2. **Port the 7 recorded cases into `scripts/selftest/selftest_gates.py`**
   — subprocess-fixture style (94 existing fixtures), CI-run, manifest-pinned,
   NOT `tests/` (frozen, TPM-authored, INV-1 — agents never edit it). This is
   the precondition for everything below: closure-repair becomes *enforceable*,
   and the tests travel with the code on backport.

### Phase 2 — Propagate (your go; before Phase 3, not after)
3. **Backport to blueprint → children**: Wave 1 (task-key skeleton), validator
   key-naming message, closure auto-repair — **code + tests together**. Do it
   while Phase 1 is warm; every later testchat-only change grows the backlog.
   **Conscious call, stated not implied:** this is backport-before-live-confirm.
   Defensible only because containment is real — `validate()` untouched (worst
   case in any child: fail to repair = today) and `|| true` swallows even a
   repair crash, leaving the un-repaired plan to `validate()` (normal
   behavior). The only thing one testchat live confirmation buys before
   fleet-wide propagation is a single real-run sanity check, ~one milestone's
   delay. Belt-and-suspenders alternative: gate Phase 2 on the first
   `closure-repair:` line in a real testchat run. Both defensible — pick one
   and say which.

### Phase 3 — The next lever (Wave-1-shaped, measure-first)
4. **id-format / never-invent-contract-id verbatim rules** — the 5/32 id
   subtype of rejections; same harness as Wave 1 (verbatim rule text in EM
   prompts, before/after shape-valid measurement). Cheap. Also shrinks the
   identical-retry population: the recurring rule IS the retry generator.

### Phase 4 — Measure, then decide (don't build blind)
5. **Re-measure the identical-retry population** post-Phase-3 (M34 re-derived
   a byte-identical brief and failed the same rule twice). If Phase 3's rules
   killed it → close the retry short-circuit as evidence-ruled-out. If it
   survives → build it. The short-circuit (don't re-call the EM when the plan
   didn't change) is only worth it if 4 doesn't eliminate the population.

### Phase 5 — The big one (own session, own harness)
6. **Spec-tier quality** — TPM-tier, root of the 60–90-min refreeze storms
   (M31 was 5-for-5 spec defects). Separate scoped pass with pre/post numbers
   like Wave 1, CEO-gated. Deliberately last: Phases 3–4 clean the
   counterfactual first (fewer rule-driven retries = cleaner attribution), and
   it is the least-bounded item — it deserves the discipline, not a bundled
   sprint.

## Standing — parallel, not sequential

- **Live confirmation watch**: first real closure-violating milestone must
  auto-pass (`closure-repair:` line in the orchestrate log) instead of
  bouncing to the EM. **Constraint: Phase 1 must land before the next
  milestone** so that when it fires, CI is already enforcing the gate — that
  is the moment "proven ≠ enforced" flips to "enforced."

## Closed — do NOT re-open (evidence-ruled-out)

- ✗ Wave 2 file-count widening — EM is load-bearing; skip-population was 3
  storm milestones (`a151f6a`).
- ✗ Wave 3 ERD trim — marginal (~3–8% of a ~280s EM call; generation-bound).
- ✗ Browser-test xdist parallelization — blocked: fixed ports 8971/8972,
  shared server + storage, serial reset. Backend-concurrent lane (~40s, ≥2
  CPUs) is the only survivor and is small.
- ✗ Identical-retry short-circuit — suspended until Phase 4 re-measures
  post-Phase-3 (likely closed by fixing the recurring rule).

## How to start the fresh thread

Point it here: *"read project-trail/2026-08-06-forward-sequence.md and start
with Phase 0, item 1."* The first line the next pass reads is the tree
cleanliness gate — same discipline the sequence is built on.
