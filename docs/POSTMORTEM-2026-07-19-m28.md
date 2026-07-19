# M28 model-dropdown milestone: two EM swaps against an impossible spec

date: 2026-07-19
status: historical
authorship: agent-drafted at CEO direction (conductor seat, CEO-session);
derived from the tree per Operating Rule 1/5 — refreeze deltas, plan
history, commit co-author trail, tasks/CURRENT.md, tasks/HANDOFF-blueprint-items.md.
Filed in testchat because blueprint's postmortems/ archive is human-authored
by its own README; move there only by CEO hand if wanted.

## What happened

M28 (catalog dropdown + eject + confirm modals) took four freezes
(v51→v54), five different models across three seats, and a manual
`[success]` bypass (`69708e4`), all between 23:34 and 01:51 overnight,
immediately after M27 closed at 22:50 the same evening. External factors:
a sudden pause/resume mid-milestone and conductor-model changes
(plans v10–v12 by Fable 5, task T7 coded by Opus 4.6, close-out by
Opus 4.7 — plus the two local EMs before any of them).

Timeline, from the tree:

- **23:34 v51 frozen.** Spec froze the `GET /api/v1/models/catalog` route
  but never added its implementing files to `contracts.files`.
- **23:49 v52 refrozen** — one-line test fix: the new AC-31 test forgot to
  click the confirm modal the same spec introduced (TPM test bug).
- **23:49→01:05** — mlx-serve qwen failed as EM; seat swapped to mtplx
  qwen; failed identically. ~75 minutes.
- **01:05 v53 refrozen.** The DELTA admits the real cause: *"no valid plan
  could contain a task that builds the catalog endpoint... Caught at the
  plan gate after two EM models failed against an impossible spec"* —
  validate-plan.py's bijection made v51/v52 unimplementable by ANY EM.
- **01:08–01:16** — frontier EM (ladder, CEO-approved). Two more recuts of
  its own: v54 added the M28c D-68 directive the spec lacked (T11 blocked
  at the gate; both local EMs had revised the wrong handler); plan v12
  recast T11 as literal edit blocks after the local coder dropped half of
  a two-part prose brief (the exact Rule 8 failure mode, on file since
  2026-06-30).
- **01:35** — T7 (app.js, the largest stateful file) done by a frontier
  coder.
- **01:51** — AC-42 (`test_thinking_placeholder_shows_then_clears`, M9-era
  timing test) failed three orchestrate retries; unrelated to the delta;
  CEO-authorized manual `[success]` with the isolate + inventory-check +
  consent guard (CLAUDE.md correction log 2026-07-19).
- **Aftermath:** eleven post-success live-fixes in app.js (5 next morning
  `6857d70`..`9da00ff`, 6-bug batch `b4c108b`) — interaction details the
  frozen ACs never pinned. First materially non-zero hand-fix milestone
  since M7.

## Root cause

1. **Every recut was a spec-layer defect; zero were execution defects.**
   v52 = TPM test bug; v53 = inventory omission; v54 = D-68 debt unswept
   at freeze. Same pattern as the M23 cost ledger ("ALL THREE spec bugs
   the TPM's"). The EM/coder seats got the operational blame (two model
   swaps, two seat escalations); the defect source was the top rung every
   time.
2. **Misattribution under pressure.** Two different models failing at the
   same gate the same way is evidence of an impossible task, not a weak
   model. The "is the spec satisfiable?" check ran only after ~75 minutes
   of varying the solver.
3. **Known lessons on file, not applied at freeze time.** D-68 legacy-file
   debt (incident #2 in the 07-17 ledger, same class) and Rule 8 atomic
   briefs (2026-06-30) were both documented and both re-fired.
4. **Context churn at the weakest joint.** The two defect-bearing freezes
   were authored 23:34–23:49, 44 minutes after closing the prior
   milestone, at the end of a long day, across pause/resume and model
   handoffs. Freeze-time omissions are the one defect class the gates
   catch only after burning the execution layer's time.
5. **AC-42 was a known debt with a written, unexecuted plan** — flagged by
   name on 2026-07-15 ("harden both at the M23 refreeze"), never hardened
   through v45–v54.

What held: no gate lied. Plan gate refused the impossible spec, D-68
refused unjustified handlers, DRIFT halted on a red suite; the one bypass
was isolated, inventory-checked, CEO-consented, documented. The system
failed slow but honest.

## What changed as a result

- v53/v54 spec corrections + M28c directive (frozen, shipped).
- CLAUDE.md correction-log row: manual-bypass guard (isolate +
  delta-inventory check + CEO consent) for any future DRIFT override.
- D-77 candidate (retry-in-isolation before DRIFT) fully specified in
  `tasks/HANDOFF-blueprint-items.md`, parked for blueprint.
- AC-42 hardening now on `tasks/BACKLOG.md` (this postmortem's commit) —
  it was promised to the backlog at close-out but never added.

## Still open (recommendations, blueprint-side unless noted)

1. **Freeze-time satisfiability preflight in refreeze.sh** — mechanically
   verify every changed contract has implementing files in
   `contracts.files` (the same bijection validate-plan.py enforces)
   before human approval. Converts v51's 75-minute detour into a
   2-second pre-freeze error. Highest single leverage.
2. **ESCALATION.md heuristic rung** — before any EM model swap, re-audit
   the spec against the plan gate; two identical failures from different
   models indict the puzzle, not the solver.
3. **D-68 debt sweep at freeze** — refreeze lists bare handlers in
   inventory files so directives like M28c are in the spec on day one.
4. **Ship D-77** (parked in the handoff file).
5. **AC-42 re-cut at next refreeze** (testchat-side, TPM lane, now
   backlogged).
6. **Soft:** don't freeze a new milestone's spec in the last hour of a
   long day; both defect-bearing freezes were.

## Lessons

- When the gate rejects every solver, audit the puzzle first. Model
  capability is the most visible variable and usually the wrong one.
- A lesson recorded as "template debt" but not yet mechanized will re-fire;
  the correction log is memory, not enforcement (CLAUDE.md 2026-06-04:
  "for must-hold rules, prefer mechanical gates over doc guards").
- A frozen suite pins the contracted surface, not feature quality: UI
  interaction detail leaks past the oracle, and the live-fix tail is the
  honest measure of that gap. Track hand-fixes per milestone.
