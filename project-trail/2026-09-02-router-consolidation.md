# Router milestone close-out + v106–v119 consolidation (2026-09-02)

## Context — how we got here

A T7-M1 broker defect (`orchestrate.sh` referenced `$attempt`, a `run_coder`
local, at the task-loop `[task]` commit site) crashed the T8 build under
`set -u` on the first live `[task]` commit of the post-M1 plane. Fixed in the
Blueprint (`6132185`, `$attempt` → `$((strikes + 1))`), pins re-advanced,
pushed.

The re-run then surfaced a **spec/brief defect** in T8's T3
(`src/api/chat.py`): the EM-composed brief placed the AC-179 not-ready
re-probe in the SSE generator's outer Python `except`, but `llm.py` collapses
a mid-stream transport failure into a **message-less `("error",)` item yielded
through the normal stream loop** — the `except` never runs for the 404 race
the oracle exercises.

**The routing mistake (logged in the correction log):** that T3 fix is one
file, ~10 lines, deterministic, with frozen tests that already pass — a
textbook D-132 *direct* candidate. Instead it was pushed back through the
milestone lane (a v116 brief-only refreeze + `orchestrate` re-run). That
choice resolved the delta baseline to **v105** and dragged in the whole
v106–v119 delta stack: a **122 KB** EM planning context (vs the 65 KB budget)
and a plan-gate halt on a stale UI file (`catalog.js`) unrelated to the fix.
T3 ultimately landed **direct** (`66c64fb`, chat.py only, 6/6 router tests
green), which is where it should have started.

## The reframe that shrank consolidation

The v119 milestone `[success]` (a parallel session's close-out, independently
audited here — real `[success]` commit, ledger hashes matching current bytes,
T4–T8 genuinely no-edit, full suite **235 passed / 0 skipped / 0 xfailed**)
**already reset the delta baseline v105→v119 for free.** So the planner-context
bloat that had blocked the re-run was gone regardless. Consolidation's
remaining value was therefore **hygiene**, not unblocking:

- the standing `ERD.md` still described the *pre-router* app — the entire
  router feature lived only in the delta stack + code, invisible to future
  planning; and
- seven frozen `test_router_route.py` ownership mappings were pinned only in
  the retiring delta stack, not in the standing `contracts.test_mapping`.

## The eight steps

1. **TPM seat** named (this session, CEO-authorized).
2. **State + effective-spec snapshot** — verified baseline v119, inventoried
   the 14 deltas (v107–v113 are the palimpsest: the router feature refrozen 7×
   on the same 3 files; v114/v117/v118 planning-only), identified the
   standing-ERD gap.
3. **Fold standing ERD** — router feature written into `ERD.md` as an
   additions-only draft; byte-exact test-visible strings (esp. the not-ready
   message); ~20 KB.
4. **v120 (behavioral bookkeeping)** — registered the 7 carried router
   ownership mappings (test_mapping 18→25) and trued the stale
   `schema:ModelInfo.source` to the frozen `Literal`.
5. **Size target** — model-facing packet confirmed < 32 KB.
6. **v121 (nonbehavioral fold)** — the folded `ERD.md` became standing, the
   active `ERD-DELTA` was **retired**, the 14 historical `ERD-DELTA-v*.md`
   snapshots kept as audit.
7. **Prove the baseline advances** — `orchestrate` close-out landed
   `[success] spec v121` (`c6d78fe`); ledger baseline moved 119→**121** (proven
   from the committed ledger, not inferred from the refreeze); all 8 tasks
   no-edit/acceptance-only; 20-test verdict green; 68 s.
8. **Confirm empty scope** — delta came back `0 re-plan / 0 new / 0 node-ids`,
   active packet **18,699 B** with no budget warning.

## Two non-obvious findings

- **Consolidation is two freezes, not one.** Registering test mappings changes
  `contracts.json` → forces *behavioral* classification, which cannot ride a
  nonbehavioral standing refresh. So v120 (behavioral, carries the mappings)
  must precede v121 (nonbehavioral, folds + retires the stack).
- **D-122 blocks invisible changes.** `test_mapping` is an
  INVISIBLE_CONTRACT_KEY — registering mappings *alone* is rejected as
  "invisible to the DELTA bookkeeping." The genuinely-stale
  `schema:ModelInfo.source` correction (a *visible* schemas-family change) was
  the legitimate carrier — the same pattern v117 used for `catalog.js`.

## Before → after

| | Before | After |
|---|---|---|
| Baseline (last `[success]`) | v105 | **v121** |
| Active EM context | 37,620 B (over budget) | **18,699 B** (under) |
| Delta scope | 14 deltas, 6-file span, 122 KB context | **empty** |
| `contracts.test_mapping` | 18 (7 router pins stranded in the stack) | **25** (complete) |
| Standing `ERD.md` | pre-router architecture | router feature folded in |

## Discipline / verification

Every freeze gated through `refreeze.sh --diff` (green preflights are the
apply verdict, D-121) before applying; **no application-code or frozen-test
changes**; historical deltas archived, not deleted; verified against the tree
at each step (completion-ledger hash match, string byte-checks, additions-only
diffs, independent full-suite re-runs). Model seat for the runs: MTPLX
`mtplx-qwen38-27b-optimized-quality` on `:8002` (confirmed non-thinking under
`llm-call.sh`'s top-level `enable_thinking:false`).

## Outcome

Clean **v121** baseline: standing ERD accurate, mappings complete, delta stack
retired, EM context back under budget. Commits (all on `origin/main` at
`8be9da4`, release-gate green): T3 direct `66c64fb`, `[success] v119`
`aa3deea`, `[refreeze v120]` `8d57b43`, `[refreeze v121]` `0a1c110`,
`[success] v121` `c6d78fe`, correction-log row `8be9da4`.

Meta-lesson (correction log, 2026-09-02): the milestone-vs-direct routing
decision is a checkpoint that fires at the moment a task fails/escalates,
BEFORE continuing the current lane — decided on size + determinism, never on
the pipeline's next mechanical step. Reciting a routing rule in hindsight is
not applying it at the fork.
