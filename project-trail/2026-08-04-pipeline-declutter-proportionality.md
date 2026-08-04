# Handoff — declutter the pipeline to fit the change (2026-08-04)

For a fresh thread. Distilled on purpose: start with signal, not the
transcript. Continues `project-trail/2026-08-03-forward-plan.md` (items #3/#4)
and sharpens it into a cut-the-ceremony mandate.

## One-line mandate
Each milestone is a minor ask — a single-file edit that takes ~1 min. The
other ~60 min is machinery guarding the *coder*, which was never the failure
surface. **Make the pipeline proportional to the change; cut ceremony that
never caught a real failure.** CEO framing, 2026-08-04.

## The test for every piece of machinery
*Did it ever catch a real failure the frozen oracle wouldn't have?*
If no → it's ceremony → candidate to cut. Apply this per pipeline step.

## Proven vs. hypothesis — hold the line
- **PROVEN (in tree / trails):**
  - The EM plan call is ~68% of wall-clock; it re-emits the **full inventory**
    every run, so plan cost scales with the whole app (~3.4k lines), not the
    delta. The actual coder edit is ~15s. Suite is ~10%.
    (`2026-07-27-m31-process-breaks.md` Part 3.)
  - The **spec tier is the failure surface**, not execution — M31 halts were
    5-for-5 TPM spec defects; coder output was correct in every task it ran.
  - **Staleness / palimpsest** is the proven root cause of recent friction
    (M32 stale ERD, M33 T4 stale brief, M33 re-run of finished tasks).
- **HYPOTHESIS (must verify before cutting):** that stripping the EM
  decomposition tier / DAG for atomic changes loses no real safety. The local
  coder is genuinely weak (4k instruction-collapse, import bugs, drops
  multi-file tasks). Prove the cut is safe with the audit below, don't assume.

## What's load-bearing (keep — small footprint)
- Frozen test as oracle — the only objective "correct" (but misses
  interaction/layout/error-path bugs; see verify-past-oracle below).
- Host suite re-run — catches sandbox-green-but-broken-on-host.
- Fail-closed on empty task-state — stopped a whole-app rewrite once.
- One-file-per-task boundary — the one guard the weak coder actually needs.

## What's fighting itself (cut or shrink)
1. **EM re-emits the full inventory** — biggest single lever. Plan must scale
   to the delta, not the app. Blueprint-level (was forward-plan #4).
2. **EM decomposition tier for atomic changes** — nothing to decompose when
   it's one edit in one file. Fast lane: spec → oracle → the one edit → suite.
   **Coding stays local** — the coder still does the edit; we drop the tier
   that adds nothing, not the local seat ([[feedback-local-coding-frontier-supervises]]).
3. **Growing spec** — v78 consolidation zeroed it; per-milestone curated brief
   keeps it zeroed (forward-plan #3).
4. **Retry ladder** — already cut: failures go straight to TPM, no re-runs
   ([[feedback-failures-escalate-to-tpm-not-em]]).

## The plan (prioritized)
1. **Evidence audit** — walk each pipeline step against the last 4 milestones
   (M31–M34); tag each **load-bearing / ceremony / cut** with the failure it
   did-or-didn't catch as evidence. This is the gate before any cut.
2. **Fast lane for atomic single-file changes** — skip EM decomposition + DAG;
   run spec/oracle → local coder one edit → suite. Draft it, self-test on a
   real minor ask, measure tries-to-green vs. the full path.
3. **EM economics** — plan scales to the delta (blueprint, parallelizable).
4. **Verify past the oracle stays** — after green, exercise the real app on the
   host for the interaction/error/layout class the frozen suite can't see.

## Standing constraints the fresh thread MUST respect
- Coding stays local; never route product code to the frontier seat — make the
  pipeline proportional instead ([[feedback-local-coding-frontier-supervises]]).
- Failures → TPM, no coder re-runs, no EM consult ([[feedback-failures-escalate-to-tpm-not-em]]).
- Coder output budget defaults to 24k, not the shipped 4k ([[feedback-coder-budget-default-20k]]).
- `models.env` is CEO-owned; per-run `SWBP_*` overrides are the sanctioned
  A/B method ([[feedback-models-env-ceo-owned]]).
- CEO gates on plain-language claims, never diffs; TPM is the approver and
  carries accountability ([[feedback-ceo-gates-present-claims-not-code]],
  [[feedback-tpm-authoring-defects]]).
- No invented taxonomies — use the project's own terms (delta, brief, refreeze,
  halt, EM plan, oracle) ([[feedback-no-invented-taxonomies]]).
- v78 consolidation is done; **delta JSONs stay** (live D-108/D-113 resolver
  infra — do not delete).

## Live state (verify, don't trust)
- `[refreeze v79]` (`b488af5`) is current head; M33 closed `[success] v77`,
  192/192 host + sandbox.
- `.pipeline-state/tasks/` is **empty right now** — that's a halt-before-run
  condition; repopulate/verify before any orchestrate run.
- Read for context: this file, `2026-08-03-forward-plan.md`,
  `2026-07-27-m31-process-breaks.md`, `2026-08-03-m33-closeout.md`.

## How to start the fresh thread
*"Read project-trail/2026-08-04-pipeline-declutter-proportionality.md and start
with the evidence audit (plan item 1)."*
