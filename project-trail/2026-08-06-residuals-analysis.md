# Residuals analysis — contract-repair Phase 3 v2 (2026-08-06)

Post-`--repair-contracts` build (`8a0e51f`/`dde1676`, backported `58b7c92`).
Answers the open question from `2026-08-04-forward-sequence.md` Phase 3:

> Residuals out of v1 scope: carried-id drift (235145, 012624) and dup task
> id (235017). Real recurring classes worth fixing, or one-offs to leave to
> the gate?

## Classification correction

The forward-sequence doc classified entry **235145** as "carried-id drift
(out of scope)." That classification was incomplete — 235145 ALSO has 24
unknown `entry_point:`-prefixed contract IDs, the same class as 004539 /
005754 / 235017. `--repair-contracts` handles these. The original "58 → 0"
count excluded 235145's unknowns; the true corpus-wide unknown-contract
count is **65** (not 58), all now repaired.

## Corpus scan (66 archived entries: 30 subtree, 18 plan, 18 diagnosis)

| Class | Entries | Rate | --repair-contracts? |
|---|---|---|---|
| Unknown contract IDs | 5 subtree + 2 full-plan | 17% of subtree | **Yes** (deterministic DROP, landed) |
| Carried task-ID drift | 2 subtree (012624: 6 renames, 235145: 1) | 6.7% | No |
| Dup task ID | 1 plan (235017: T12 x2) | 2.1% | No |

### Carried task-ID drift (2 entries, 7 renames total)

**Mechanism:** the EM is instructed to preserve carried task IDs from the
parent plan when planning a subtree. It ignores this and assigns fresh IDs
(e.g. T3→T5, T12→T20). Same prompt-compliance failure class as the Phase 3
id-format rule (0/5).

**Evidence:**
- `012624` meta: 6 violations — T3→T5, T12→T6, T11→T7, T5→T13, T6→T14, T7→T15
- `235145` meta: 1 violation — T12→T20

**A deterministic fix exists:** remap returned task IDs to match the carried
plan's file→ID mapping in `cmd_merge_subtree`, updating all `depends_on`
references. Same monotone-repair pattern as `--repair-contracts`. Lives in
merge logic, not post-emit repair.

### Dup task ID (1 entry)

**Mechanism:** the EM named two tasks T12 (settings.py and models.py).
Single instance, 2.1% rate.

**No clean deterministic fix:** which copy keeps the canonical ID is
ambiguous, and a dup may signal confused decomposition, not just a naming
collision.

## Decision

**Both: leave to the gate.** Rationale:

1. The gate catches both classes reliably. The EM retries and the second
   attempt typically succeeds.
2. The retry cost is one extra EM call per occurrence — not a refreeze
   storm.
3. Carried-id repair would touch `cmd_merge_subtree`, adjacent to the
   `--repair-contracts` build that just landed. Merging both increases
   blast radius for a 6.7% hit rate.
4. Dup-task-id is a one-off (single instance in 48 plan entries).

**Revisit post-Phase 4** only if:
- The carried-id retry rate increases after `--repair-contracts` changes
  the population of plans reaching the merge step, OR
- Dup task IDs recur (track via archived `meta.txt` `plan_gate_errors`).

## Verification of --repair-contracts landing

Checked same session, all clean:
- Testchat: `8a0e51f` (7 selftests) + `dde1676` (wiring + 1 selftest) — 8/8 green
- Blueprint: `58b7c92` (byte-parity, combined) — manifest clean
- Position: line 938/915, after `--repair-closures`, before gate — correct
- `|| true` guarded, `plan.json` conditional — correct
