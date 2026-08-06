# Milestone run timing — reconstructed accounting (2026-08-06)

Answers "total time per milestone + where it went," reconstructed from **git
commit timestamps + `.em-archive`**. The pipeline's own per-phase timing
(`timings.tsv`, written by `orchestrate.sh:216`) was **not retained** —
`.pipeline-state` is gitignored and testchat's was wiped — so exact per-phase
minutes for these runs are unrecoverable. Elapsed spans are reliable (commit
timestamps); the per-phase split below is a floor, not a full accounting.

## The headline
**Elapsed time is dominated by the human/spec loop *between* pipeline bursts,
not by machine compute.** The pipeline's active work is minutes; the runs are
hours. Shaving machine-time cannot move an elapsed hour that is mostly gap.

## Last three milestones (all rows verified against the tree)

| Milestone | Spec | Run span (refreeze → `[success]`) | Archived EM activity | The rest (unrecorded) |
|---|---|---|---|---|
| **M32** | v71 | **57 min** (07-28 02:52 → 03:49) | 5 calls, ~5 min | coder + suite + gaps |
| **M33** | v77 | **4h 28m** (08-02 21:34 → 08-03 02:02) | 3 calls, ~15 min | incl. T2/T3/T4 re-exec (~25 min, spec-defect storm) |
| **M34** | v79 | **~5h 42m** (08-03 22:05 → 08-04 03:47) | 5 calls, ~6 min | **~5.5h** coder + suite + human/spec gaps |

So the machine's recorded activity is **~5–15 minutes** inside runs of **1–6
hours**. The remainder is coder execution + the ~5-min sign-off suite + the
dominant human/spec-rework gaps.

## Two findings from the reconstruction
1. **M34 ran against a *staged* spec.** v79 EM calls started **22:05:21** —
   **~1h 9m before** `[refreeze v79]` was committed (**23:14:27**). The run was
   driven off the staged-but-uncommitted spec, then the freeze landed mid-run.
2. **v78 is not anomalous.** 16-min run, 12 tasks, **0 archived EM calls**
   (`[refreeze v78] 19:04 → [success] 19:20`). v78 is the **consolidation
   refreeze** (retires the accumulated delta stack) — non-behavioral, so it hits
   the `em_needed=0` mechanical path: no EM decomposition, fast merge. This is
   the proportional pipeline working **as designed**, and a live data point that
   the no-EM fast path fires on consolidations.

## Data-quality caveats (so the next reader doesn't over-trust the numbers)
- **`.em-archive` is a partial, lossy record.** v78 has zero entries despite a
  real run; M34's archive window ended ~82 min in (23:27) while the run
  continued ~4.3h to `[success]`. "Archived EM activity" is therefore a **floor**.
  (An earlier pass mistook the 82-min archive window for the whole M34 run — it
  was ~5.7h; corrected here.)
- **Per-phase minutes are unrecoverable** for these runs (`timings.tsv` wiped
  with `.pipeline-state`). The M31 hand-captured profile remains the only
  itemized reference: a clean pass ≈ 7 min, planning call ~68%, suite ~10%.
- **Elapsed spans are solid** — straight from `[refreeze vN]` → `[success vN]`
  commit timestamps.

## Implication for the "milestone efficiency" metric
The time that actually accumulates is the **spec-rework loop** (multi-cycle
refreezes — M33 was 5 cycles v73→v77) and human review between bursts — not the
pipeline steps. That is why **spec-tier quality (forward-sequence Phase 5)** is
the real time lever, and why pipeline-compute optimizations (ERD trim, etc.)
were correctly ruled out.

## Retention note (deferred, low value)
`orchestrate.sh` already captures `timings.tsv`; only retention is missing
(persist `feature-summary.py` at `[success]`). Deferred: it would fill only the
**minutes** layer, which this table shows is the small part. The dominant
**elapsed** layer is already derivable from git with zero instrumentation.
