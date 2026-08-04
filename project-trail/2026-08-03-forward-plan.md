# Forward plan — spec context hygiene (2026-08-03)

Handoff for a fresh thread. Distilled on purpose: the next session should
start with signal, not the whole transcript — that *is* the point below.

## One-line diagnosis
testchat's friction is not the coder (27b handles atomic tasks) and not the
app (~3.4k lines). It's the **specification**: a standing PRD/ERD that only
ever grows. Every freeze hands the TPM the full frozen spec with "derive any
delta from THIS"; under a no-regressions oracle, **adding is always safe and
pruning always risky**, so it accretes — including stale, superseded content
the coder then faithfully builds against.

## Proven vs. hypothesis — hold this distinction
- **PROVEN (verified in tree):** *staleness* breaks it — contradictory /
  superseded content sitting live in the spec, executed against the wrong
  reality (T4 tonight; the M32 stale-ERD chain). Evidence:
  `project-trail/2026-08-03-m33-closeout.md`,
  `project-trail/2026-07-27-m31-process-breaks.md`.
- **HYPOTHESIS (not isolated here):** *volume/bloat* of even-correct context
  dilutes the model and degrades it. Real general LLM principle, likely
  contributes — but NOT measured in this system. Do not bet the architecture
  on it before testing (item 2).

## Design principle agreed
Not "dump everything" (no LLM, frontier included, does the right job over a
bloated whole) and not "new-feature-only" (the stateless local LLM can't fill
the gaps). The middle: **the frontier TPM curates the right-sized slice** —
new feature + the past relevant to THIS change — for the local EM/coder.
Relevance-selection is the TPM's real value-add. Because it will sometimes
mis-size, two safety hatches are mandatory, not optional:
(a) **ask back** on ambiguity/insufficiency, (b) **assume-then-correct** via
the existing escalation ladder.

## Already done this session (baseline — verify, don't trust)
- ui-walk gate bug fixed: refreeze contract-delta walk now includes `ui`
  (blueprint `0a80905`, selftested red→green; synced to testchat `68ae9db`).
  Last of the five M31 gaps with no mechanical guard.
- M33 closed: `[success] spec v77`; 192/192 host AND sandbox. Re-execution
  incident (over-wide delta + stale brief re-ran finished tasks) recorded in
  `project-trail/2026-08-03-m33-closeout.md`.

## The plan (prioritized)
1. **Consolidation refreeze (v78)** — testchat-only, safe, do regardless.
   Rewrite the standing PRD/ERD to describe only *today's* system; drop
   superseded ACs; retire stale change-notes. **No new tests** (coverage
   already present — verified). **Delta JSONs STAY** (live D-108/D-113
   resolver infra — do NOT delete them). Zeroes the debt. ~1 focused session,
   CEO-gated at the freeze on plain-language claims.
2. **Validate the hypothesis** — cheap experiment *before* the big change.
   One real milestone, run twice: full standing PRD vs. lean TPM-curated
   brief. Measure tries-to-green / coder strikes / EM revisions. Settles
   whether context-hygiene is THE lever or just A lever. Uses existing
   per-run `SWBP_` overrides + timing logs.
3. **Structural fix — per-milestone spec + TPM-as-curator** (the durable one;
   gate on #2). Cumulative source of truth = frozen tests + contracts
   (already). What EM/coder see = a per-milestone brief (new feature +
   TPM-selected relevant history). Make context-sizing an explicit TPM
   responsibility and wire the ask-back / correct hatches. Lives in the
   **blueprint** → affects every child project → highest stakes → deliberate,
   CEO-gated.
4. **EM economics (same principle, second surface)** — the EM is *also*
   handed the whole file inventory every run (~68% of wall-clock; scales with
   the app, not the change). Make its plan scale with the delta. Independent
   win, blueprint-level, parallelizable.
5. **Two guards from tonight (small, mechanical)** — (a) an over-wide delta on
   a *done* milestone re-runs finished tasks; (b) plan briefs outlive the spec
   versions that shaped them. Guard, or fix the byte-identical-restage
   workaround that widens deltas.

## Suggested order
#1 and #5 now (safe). #2 to test the theory. #3 only if #2 confirms, done
carefully in the blueprint. #4 in parallel anytime.

## How to start the fresh thread
Point it here: *"read project-trail/2026-08-03-forward-plan.md and start with
item 1."* That hands the next session the slice, not the transcript.
