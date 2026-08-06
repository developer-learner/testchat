# Phase 4 — Pre-registered gate design (2026-08-06)

Pre-registered measurement and decision criteria for the identical-retry
short-circuit, per `2026-08-04-forward-sequence.md` Phase 4:

> Re-measure the identical-retry population AFTER Phase 3. If the rules
> killed it → close as evidence-ruled-out. If it survives → build it.
> Suspicion: Phase 3 eliminates this. Verify before spending.

## Definitions

**Retry sequence:** consecutive archived EM entries at the same
`spec_version` and type (plan/plan-subtree), excluding diagnosis calls.
A sequence of length N has N-1 consecutive pairs.

**Identical-retry pair:** a consecutive pair where entry A was
`plan_gate=rejected` and entry B was rejected with the *same primary error
class*. Primary error class = the first `PLAN GATE FAIL:` reason, classified
into one of: `unknown-contract-id`, `carried-id-drift`, `dup-task-id`,
`browser-test-closure`, `outside-delta-scope`, `incomplete-task-object`,
`no-tasks-array`, `test-contract-mismatch`, `node-id-not-frozen`,
`unmapped-node-id`, `module-level-import`, `brief-too-long`, `missing-tasks`.

**Retry short-circuit:** a hypothetical mechanism that detects "the EM will
fail the same way again" and halts before making the call.

## Counting method

Source: `testchat/.em-archive/*/meta.txt` (`plan_gate`, `plan_gate_errors`)
and `reply.json` (for content-identity hash).

1. Build all retry sequences (consecutive same-spec, same-type).
2. For each pair where A was rejected: classify A's and B's primary error.
3. Pair is *identical* if same primary error class AND B is also rejected.
4. For each identical pair, trace what happened after B (passed? exhausted
   max revisions? error evolved?).

## Baseline measurement (archive as of 2026-08-06)

### Population

| Metric | Count |
|---|---|
| Archived EM entries (plan + subtree) | 48 |
| Retry sequences (length > 1) | 12 |
| Total consecutive pairs from a rejected entry | 26 |
| **Identical-retry pairs** | **9 (35%)** |
| Different-class or fixed-on-retry pairs | 17 (65%) |

### Identical-retry pairs by error class

| Error class | Pairs | Fixed by --repair-contracts? | Fixed by --repair-closures? |
|---|---|---|---|
| browser-test-closure | 3 | No | Partially (1 maybe; 2 have cycle — structural) |
| outside-delta-scope | 1 | No | No |
| test-contract-mismatch | 1 | No | No |
| node-id-not-frozen | 1 | No | No |
| no-tasks-array | 1 | No (REPLY IDENTICAL — only case) | No |
| incomplete-task-object | 1 | No | No |
| module-level-import | 1 | No | No |

**Zero** of the 9 identical-retry pairs involve `unknown-contract-id` errors.
All unknown-contract-id retries produced a *different* error class on the next
attempt — the error evolves, it doesn't repeat. The two populations (identical
retries vs. unknown contract IDs) are disjoint.

### What happened after each identical pair

| After the identical pair | Count | Meaning |
|---|---|---|
| Next attempt passed | 2 (22%) | Retry mechanism worked — short-circuit would block a success |
| Hit max revisions (sequence ended) | 4 (44%) | Wasted retries — short-circuit would correctly save them |
| Error evolved to different class, still failing | 3 (33%) | Mixed — retries didn't help directly |

### Detail

```
node-id-not-frozen     → 3rd try PASSED
test-contract-mismatch → EXHAUSTED (max revisions)
browser-test-closure   → error evolved (→ dup-task-id → carried-id → scope)
outside-delta-scope    → error evolved (→ unknown-contract → missing-tasks)
browser-test-closure   → same error again → EXHAUSTED
browser-test-closure   → EXHAUSTED
no-tasks-array         → 3rd try PASSED (despite REPLY IDENTICAL on 2nd)
incomplete-task-object → EXHAUSTED
module-level-import    → EXHAUSTED
```

## Decision criteria

### Build threshold

The short-circuit is worth building only if ALL of:

1. **The population survives Phase 3 v2** — i.e., identical retries still
   occur with `--repair-contracts` + `--repair-closures` in the loop.
2. **The false-positive rate is acceptable** — a short-circuit that blocks
   retries which would eventually succeed does more harm than good.
3. **The cost of the retries is material** — either wall-clock time per
   retry or dollar cost per API call.

### Evaluation against criteria

**Criterion 1 — population survival:** YES, the population survives.
Phase 3 v2 does not touch any of the 9 identical-retry error classes.
The suspicion ("Phase 3 eliminates this") is **wrong** — the two
populations are completely disjoint.

**Criterion 2 — false-positive rate:** FAILS. 22% of identical-retry
pairs (2 of 9) lead to eventual success on the next attempt. A
short-circuit that halts on "same error class" would block those
recoveries. Even the stricter "reply content identical" test has a
false positive: the only REPLY IDENTICAL pair (no-tasks-array) passed
on try 3.

**Criterion 3 — cost materiality:** FAILS. All EM calls are local LM
(zero API cost). Wall-clock cost: 9 pairs × ~2 min/call = ~18 min of
wasted pipeline time across the entire archive (roughly one month of
development). The build would take 2-3 hours.

### Verdict

**CLOSE as evidence-ruled-out.** Three independent reasons:

1. Phase 3 v2 is irrelevant to this population (disjoint error classes).
2. A naive short-circuit has a 22% false-positive rate (blocks successful
   retries).
3. The cost it would save (~18 min/month at zero dollar cost) does not
   justify the build time (2-3 hours) or the added control-plane
   complexity.

The retry mechanism is working correctly: the feedback loop (gate errors
fed back to the EM prompt) demonstrably helps the EM produce a different
plan on the next attempt — even when the error class repeats, the plan
content usually changes (only 1 of 9 pairs had byte-identical replies).

## Post-Phase-5 re-check

Phase 5 (spec-tier quality) may change the retry population by reducing
spec-defect-driven rejections. If the identical-retry rate increases
*relative to total retries* after Phase 5, revisit — the population
would then be dominated by model-quality failures (structural JSON, scope
violations) that spec fixes can't reach.

Re-measurement method: same as above, run against the post-Phase-5
archive. Decision criteria unchanged.
