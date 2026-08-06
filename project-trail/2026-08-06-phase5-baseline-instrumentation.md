# Phase 5 baseline + milestone-run instrumentation (2026-08-06)

Before-numbers and the capture mechanism for the spec-tier (TPM) quality work.
The after-measurement runs on the first post-Phase-5 feature milestone; this
doc is the comparator it will be judged against.

## A. Before-numbers (spec-tier storm costs, from correction log + git)

| Milestone | Spec versions | Storm evidence | Cost class |
|-----------|--------------|----------------|------------|
| M28 (v51/v52) | 2+ | Unimplementable spec — TWO different EM models failed identically; ~75 min of model swaps + a seat escalation against an impossible spec (D-79 born) | S1 unimplementable |
| M29 (v54-era) | — | ACs specified mechanisms, not outcomes (unload tests assert MagicMock send_signal); 77-AC lint, 5/8 process-lifecycle ACs fail; sandbox-privilege mismatch (psutil on macOS) | S5 AC shape + S8 env |
| M31 (v54→) | storm | **5-for-5 spec defects** in one batch; 60–90 min refreeze storms per milestone | S1/S2/S4 mix |
| M32 (v67–v71) | **5 versions** | Stale ERD guidance: six removed UI lines took five spec versions; validator enforced D-64 without the EM prompt stating it (D-107 born) | S2 stale ERD |
| M33 (v72–v77) | **6 cycles** | Stale briefs (v74 artifacts vs v77 oracle): T4 brief mandated installing BOTH data.threads and data.revision, oracle wants revision only — coder built the brief faithfully, oracle rejected twice; ~25 min + 4 coder calls for done work; ~26.5 h total plan-loop wall over 6 cycles | S3 stale briefs + S4 restaged |
| M34 (v78–v79) | 2 (consolidation) | EM plan calls ran against the STAGED spec (calls predate the [refreeze v79] commit); ~5 h 42 m run | S6 staging discipline |

Refreeze-cycle counts per milestone (git `[refreeze vN]` commits): the storm
period (M32/M33) averaged 5–6 versions per milestone vs 1–2 when healthy.

## B. Defect taxonomy

Spec-tier (Phase 5 target — TPM-rooted):
- **S1 Unimplementable spec** — unsatisfiable contracts (M28; D-79 audit exists)
- **S2 Stale ERD guidance** — ERD-DELTA mismatch / standing ERD drift (M32; D-107)
- **S3 Stale briefs vs oracle** — plan briefs older than the current oracle (M33; D-107 retire-on-refresh)
- **S4 Restaged identical tests** — changed_tests carrying byte-identical tests (M33/M31 palimpsest; consolidation refreeze)
- **S5 ACs as mechanisms not outcomes** — unverifiable acceptance criteria (M29; spec lint at refreeze)
- **S6 Spec-staging discipline** — EM consuming staged-not-frozen spec (M34)
- **S7 ERD section size feeding brief overruns** — 266-char ERD section → 2541-char brief > 2500 cap (archive 2026-08-03, T7)
- **S8 Environment/sandbox privilege mismatch** — green sandbox, red host (M29 psutil; backlog: drop root)

EM-tier (gate-handled, NOT Phase 5's target — archive 66 entries: 32
rejections / 9 ok):
- unknown-contract-id (2 entries — **now deterministic-impossible**, Phase 3 v2)
- carried-id drift (2), dup task id (1) — residuals, gate-rejected by design
- unparseable/incomplete replies (5), browser closure D-64 (6), route/import closure (3),
  decomposition-incomplete mapping (6), outside-delta-scope files (3), missing
  task for file (1), no-acceptance-signal (3), over-mapped node-id (1),
  brief-too-long (1)

## C. Milestone-run instrumentation (closes the retention gap)

**Gap proven 2026-08-06:** `$LOG_DIR` (.pipeline-state/logs) is removed by the
success teardown; orchestrate stdout is retained nowhere; timings.tsv is
wiped. Only .em-archive (per-EM-call) and git survive — M32/M33/M34 timing was
reconstructed from git, not measured.

**Design (monotone, write-only, zero behavior change):**
1. **`exec` tee alternative — terminal-event capture:** the existing exit trap
   (:249) already writes run-exit.log. Extend it: at every terminal event
   (success, halt, die) copy `$LOG_DIR/timings.tsv` + the run's stdout capture
   into `.measurement/<run-ts>-<outcome>.json` — a NEW gitignored dir (same
   precedent as .em-archive, survives the .pipeline-state wipe). JSON shape:
   spec_version, outcome, wall seconds, timings rows, counters (below).
2. **Counters (derived from stdout lines, no new writes in the hot path):**
   EM plan revisions, EM consults, coder calls + revisions, `closure-repair:`
   firings, `contract-repair:` firings, SPEC-DEFECT (D-79) halts, drift halts,
   escalations.
3. **Identical-retry counter (Phase 4's population, captured live):** in
   `ensure_plan`, hash the `verrs` feedback string per revision; when the hash
   equals the previous revision's hash → `identical_retry_count++` (a
   deterministic, model-free measure of "same rejection, re-emitted"). This is
   Phase 4's measurement without any replay or seat compute.
4. **Guardrail + guard:** all copies `|| true` (measurement never blocks the
   pipeline); `.measurement/` added to .gitignore/.dockerignore; one static
   selftest asserts the trap's .measurement copy lines exist (anti-drift).

## D. Pre-registered Phase 5 acceptance (after-measurement, next feature milestone)

Against this baseline, the post-Phase-5 milestone must show, per milestone:
- **Refreeze cycles: ≤ 2** (baseline 5–6 in the storm period)
- **Spec-defect halts/defects: 0** from classes S1–S7 (baseline: M31 5-for-5,
  M32 5 versions, M33 2 documented)
- **Storm duration: < 30 min** refreeze-to-green (baseline 60–90 min)
- **Identical-retry count: ≤ 1** (the Phase 4 population; if it survives at
  scale, Phase 4 builds the short-circuit — if the spec tier killed it, the
  counter closes Phase 4 as evidence-ruled-out)

Any single metric not met → Phase 5 reverts or iterates (measure-first
discipline; no silent credit).
