# Handoff — make the EM/coder context proportional to the change (3-wave plan)

**Type:** design proposal, pre-implementation, **revised after independent LLM
review**. **For:** the implementing session (and any further review). **Status:**
nothing built. This supersedes the single-change "scope the EM context" pitch;
that idea survives as **Wave 3**, demoted behind two cheaper levers.

## Headline (what changed after review)
The original pitch led with context-scoping. Review — verified against the tree,
5/5 checkable claims confirmed — showed that was the wrong first move: it saves
only ~10–35s of prefill, under-weighted its one real risk, missed a code path
that makes its easiest part trivial, and fixed 1 of 5 call sites. **Revised
plan: schema-verbatim fix + fast-path widening first (cheap, high-yield, and
they isolate the failure hypotheses); context-scoping as a measured third wave,
replayed on the archived corpus before it ships.**

## How to use this document
Do **not** trust the numbers — re-derive them (§Verify). This analysis hit two
silent zsh bugs (unquoted `$var` doesn't word-split; `\b` aborts a bare grep),
each of which nearly produced a confidently-wrong result; the review then caught
a registry undercount and a "risk" that was already-solved code. Assume more of
both remain. Your job is to break this, not ratify it.

## Anchor (verify first)
- `testchat` at HEAD `21739fc`, spec `VERSION 79`.
- `scripts/orchestrate.sh` + `scripts/validate-plan.py` are **template-provided**
  (`.template-version` ref `abc7f6dc2c2d` == blueprint HEAD) and **control-plane**
  → every wave here is a **blueprint-level, approval-gated** change that flows to
  all child apps and needs a `.control-plane-manifest` refresh.
- Line numbers are at HEAD `21739fc` and drift; the grep anchors are durable.

---

## Shared background (unchanged, verified)
- **Coder** (local LLM): one file, gets a per-file *brief* + file content, emits
  anchored SEARCH/REPLACE diffs (D-59), **at half output budget for edits**
  (`SWBP_CODER_EDIT_MAX_OUTPUT`, orch:654). Already diff-scoped.
- **EM** (mid-tier local LLM): one completion → `tasks/plan.json` (a DAG of
  one-file tasks + briefs + mapped node-ids). The call under review.
- **PRD.md** (351 lines) is **not** fed to EM/coder — out of scope for run cost.
- Context is assembled by `build_context()` (orch:~550), which `cat`s each
  whole file in. The whole-app ERD (252 lines) + whole registry (**123** entries:
  entry_points 34 + routes 15 + schemas 21 + errors 4 + externals 3 + ui 46, in
  a 556-line `contracts.json`) ride on **every** EM call — 5 sites: orch **1016**
  (subtree plan), **1027** (full plan), **1044** (diagnosis), **1475**/**1649**
  (retry plans) — plus the coder at **654**.
- Evidence the bloat bites the local seat (`project-trail/2026-08-02-0731-model-add…`):
  EM prompt ~15k tok; ctx bumped 16384→32768 "for EM prompts"; repeated
  `finish_reason=length`; schema-guessing (`plan`↔`tasks`, `test_nodes`↔`tests`)
  with the plan *content* consistently correct.

## Two entangled failure hypotheses (the plan must separate them)
- **H1 (context bloat):** the long, noisy prompt degrades the local model →
  length-halts + schema slips.
- **H2 (schema gap, D-107-class):** the EM prompt never enumerates the six
  required task keys verbatim, so the model guesses key names regardless of
  prompt size.
Both are plausible; the model-add halts fit H2 at least as well as H1. **Do not
ship a context change while these are entangled** — Wave 1 exists to separate
them.

---

## Status — measured 2026-08-04

**Wave 1: APPLIED (testchat prototype) + MEASURED + validator message fixed.**
Both edits uncommitted, control-plane, `testchat first`:
- `EM_TASK_KEYS` injected at all 4 plan-emission sites (`orchestrate.sh`).
- `validate-plan.py` subtree messages now name expected/missing/unexpected keys
  — the fix that makes this failure class visible (the opaque "not a complete
  task object" nearly caused a misreported conclusion this session).

**Measurement** (5 key-shape entries, live qwen seat, baseline vs +skeleton,
`scratchpad/wave1_replay.py`):

| | shape-valid | length-halt |
|---|---|---|
| baseline | **1/5** | 0/5 |
| +skeleton | **4/5** | 0/5 |

Meets the pre-registered bar (shape UP **and** length FLAT). Fixed 111814 /
111932 / 113649; **113252 stayed broken**; 025709 clean both ways.

**Two evidenced findings:**
1. The **production qwen seat reproduced the guess at baseline on 4/5** — so
   Wave 1 is a **proven production-seat fix, not weak-seat insurance** (this
   corrects the earlier "insurance" framing).
2. Every baseline reply had the correct top-level `tasks` (`top_tasks=1`) — the
   `plan`↔`tasks` guess did NOT reproduce on qwen; **all failures were per-task
   key level**. Wave 1's measured effect is on per-task keys specifically.

**Resample (3× per entry, 15 samples/variant, replies saved) — CONFIRMED
2026-08-04:** baseline **2/15** shape-valid → skeleton **14/15**, length-halts
flat 0/15 both. The single-pass 1/5→4/5 understated it. **113252 resolved:** all
3 of its +skeleton replies produced the correct 6-key shape — its single-pass
miss was **stochastic noise, not a prompt-extension gap** (reviewer hypothesis
refuted). The one remaining skeleton miss (111814, 1/3) is variance → ~93%
effective, not 100%. Even the known-clean control (025709) guessed once at
baseline (2/3). Net: strong, consistent Wave-1 effect; the pre-registered bar
(shape UP, length FLAT) is met decisively.

**Strategic read:** flat length-halts + the schema fix helping strengthens **H2
(schema gap) over H1 (context bloat)** — which argues AGAINST spending on the
Wave 3 ERD trim before Wave 2 and the mapping/coverage rules.

**Failure mass — full `*_plan*` corpus (48 entries):** mapping/coverage **27**,
valid 12, key-shape **5**, truncation **4**. Wave 1 addresses the key-shape 5;
the dominant 27 need the mapping/coverage prompt-rule fix (item 2 below). **None
of this session's verified wins are milestone-speed levers** — they are
reliability only.

**→ Wave 2 AUDITED (2026-08-04) — file-count widening NOT worth building.**
Evidence (79-version delta history + archived plans):
- `trivial_construct` **never fired in its lifetime** — 0 single-file-no-contract
  deltas since the subtree machinery landed (~v54/M28 base; `trivial_construct`
  "Cut 2" itself only since 2026-07-27, ~v68-era). Dead code, not a widen target.
- Widening to multi-file-all-existing covers **only 3 distinct milestones**
  (v68; v69–71; v73–77) — **all refreeze-retry storms**. (A looser
  multi-file-no-contract count gives 5, incl. v65/v66, but those have NEW files
  → EM needed anyway.)
- On every candidate the EM **rewrote** briefs across spec bumps (7–33%
  similarity — the 100% rows are within-version retries), because the spec
  changed. Load-bearing work; a mechanical carry would freeze a stale brief →
  oracle red → EM-via-consult anyway. No time saved, a wasted coder attempt added.
- The motivating case **M34 (v79) had a contract change** (`schema:ModelInfo`,
  `CatalogEntry`) → EM genuinely needed. Its EM call was not waste.
- **Conclusion: the EM's plan call is load-bearing, not ceremony. Do not build
  file-count Wave 2.**

**Real levers (evidence-ranked):**
1. **Spec-tier quality** — root of the refreeze storms (M31 5-for-5 spec defects;
   the v69–71 / v73–77 storms). Biggest, TPM-tier.
2. **Verbatim mapping/coverage rules (D-107-style)** — the dominant failure class
   (27 of 36 plan-family rejections) AND the recurring retry rejection: M34's
   second episode re-derived a **byte-identical** brief and failed the **same**
   `mapped test file … imports` rule **twice**. Same shape of fix as Wave 1's
   task-key skeleton.
3. **Identical-retry short-circuit** — do not re-call the EM when the plan did
   not need to change (byte-identical re-emission verified on M34). Connected to
   #2: fix the recurring rule and the retry vanishes.

Wave 1 is the one shipped win. Wave 3 (ERD trim) and suite parallelization remain
not-worth-it. **File-count Wave 2: closed — do not build.**

**UPDATE — closure auto-repair BUILT (commit `f757bb4`, 2026-08-04).** Lever #2's
biggest chunk shipped: `validate-plan.py --repair-closures` + `ensure_plan` wiring
auto-fixes the **10/32 closure rejections** (D-64 browser / import / route) by
adding the `depends_on` edge the gate already computes — only when acyclic; a
would-be cycle is left for `validate()` to reject (identical to today). `validate()`
is UNCHANGED and runs after, so safety is architectural (a repair bug can only fail
to repair, never pass a bad plan). Monotone (edges push tests later only). Verified
by a 9-case synthetic gate + real-file CLI smoke; clean plans byte-unchanged.

**OPEN — ephemeral-gate finding (NEXT PASS):** the 9-case synthetic gate ran green
but is **not in the tree** (`f757bb4` ships no test file), so a regression can't be
caught later. Per Rule 6, "proven" ≠ "enforceable" until the suite lives in-repo.
Not a safety issue (`validate()` backstops), but do this next: **port the cases
into `scripts/selftest/selftest_gates.py`** — the CI-run, manifest-pinned
control-plane test file, subprocess-fixture style; NOT `tests/` (that's the frozen
INV-1 app suite). Cases: (1) repair adds the exact route edge; (2) adds the import
edge; (3) browser test gains all tasks (closure=all); (4) reverts an edge that
would cycle → `validate()` still rejects; (5) byte-unchanged no-op on a clean plan;
(6) never self-deps; (7) already-satisfied closure → no edge. The import-owner case
(created-file absent on disk) is ONLY reproducible synthetically. The working
importlib version was in scratchpad `test_repair_closures.py` (ephemeral).

**NOT YET exercised in a live orchestrate run** (Rule 6): the mechanism is unit- and
CLI-proven; the first real closure-violating milestone is the live confirmation.

---

# The 3 waves (in order)

## Wave 1 — Schema verbatim in the EM prompt (do first)
**Change:** add the literal six-key task skeleton
(`{id, file, depends_on, brief, contracts, tests}`, keys exactly, no others —
`test_nodes`/`acceptance`/`regression`/`status` rejected) to the EM plan
instruction, mirroring how D-107 already put D-64 / empty-contract rules verbatim
in the prompt. ~2 lines, the **4 plan-emission sites** (orch 1016/1027/1475/1649,
all `plan.schema.json`). The diagnosis call (1054, `diagnosis.schema.json`:
task_id/verdict/reason/revised_brief) is a *different* schema — out of scope for
the task-key skeleton. **Risk: near-zero** (adds a constraint the validator
already enforces).
**Why first:** isolates H2 from H1 at almost no cost.
**Gate/measure (pre-register) — this IS the H1/H2 separator and Wave 3's
precondition:** replay the `.em-archive` corpus by **re-sending each `.em-archive/*_plan/prompt.txt` with vs without the
skeleton** through the EM seat (NOT `em-bench.sh` — it replays *diagnosis* calls
only, not plan calls; a small plan-prompt re-send harness does this),
schema-line present vs absent, tracking **two metrics independently**:
(a) schema-guessing rate (`plan`↔`tasks`, `test_nodes`↔`tests`) and
(b) `finish_reason=length` rate. **Expected clean signal: (a) drops while
(b) stays flat** — a verbatim schema changes key-guessing, not prompt size.
Length-halts that *survive* Wave 1 are then attributable to H1 (context) and are
what justifies attempting Wave 3; if they vanish here, Wave 3 has no case either
way. **Success = fewer schema-shape rejections with length-halts unchanged.**

## Wave 2 — Widen the EM-less fast paths — ✗ AUDITED 2026-08-04: NOT worth building (see Status block)
**Change:** extend `em_needed=0` (docs/test-only merge, orch:964) and
`trivial_construct` (one-file, no-contract-change, orch:986) to cover more minor
deltas — i.e. more single-file additive changes get their subtree **constructed
mechanically with no EM call at all**.
**Why:** skips the **entire ~280s EM call**, not 30s of prefill. This is the
biggest per-milestone time win available and it already has proven precedent
(both paths exist and work today).
**Gate (pre-register) — two parts:**
1. **Evidence audit** — for each delta class the EM currently handles, did the
   EM's judgment ever change the plan vs a mechanical construction, or catch a
   failure the frozen oracle wouldn't? Widen only where the answer is "never."
   (The mandate's own machinery test.)
2. **Corpus replay** — take the archived EM calls the *widened* rule would now
   skip and run them through validate-plan.py's `--construct-one-file` +
   `--merge-subtree` path;
   confirm the resulting plans still validate. Without this, "proven-in-kind"
   stays a hypothesis: the two existing fast paths prove the *mechanism* works,
   not that it covers the *newly-included* delta classes.
**Success = more deltas take a no-EM path, the mechanically-constructed plans
still validate on replay, and no rise in downstream brief-rejections or
oracle-red.**

## Wave 3 — Scope the EM/coder context to the delta (measured, last)
**Change:** for the subtree path, build a proportional context instead of the
whole-app dump — applied to **all 5 EM sites + the coder (654)**, one policy:
*context proportional to the task*.

Build it from **existing machinery** (review-confirmed):
| Send | Source | Note |
|---|---|---|
| `ERD-DELTA.md` | as-is | the change |
| ERD **section(s) for the changed files** | **`_erd_mass_per_file` (validate-plan.py:872)** | file→section slicer **already exists**, tuned vs M31 app.js overshoot — this is today's work, not research |
| contract entries for changed files | `contracts.files` == `changed_files` (== the 2 delta files, the exact slice set) | |
| flat list of **all valid contract-id names** | registry keys | preserves the never-invent-an-id rule while dropping full schemas |
| `carried-plan` (id, file, depends_on) | as-is | note: **carried briefs are NOT passed** (orch:1015, "briefs omitted deliberately") |
| `map_nodeids` | subtree scope | |

Target ≈900+ lines → ≈150–250.

**The one real risk (was under-weighted):** the **contract-registry slice** for
**new-file** tasks. Existing files are lower-risk — the change is described in the
delta, the coder gets file content, the oracle is the backstop — but a
brief-wrong → oracle-red → retry *is* the ~280s cycle this wave exists to kill,
so a bad slice is self-defeating. **Mitigation (closes it): new-file tasks fall
back to full emission if the slice can't cover them.** Existing-file risk is then
just brief-completeness, caught by the oracle; the id-namespace guard covers
invention.

**Gate — replay before shipping (the "measure before selling" the reviewer
demanded):** the same plan-prompt re-send harness as Wave 1 (NOT `em-bench.sh`,
which is diagnosis-only) on the `.em-archive/*_plan` corpus, scoped context vs
current, measuring length-halt rate, plans-per-attempt, valid-plan-first-try.
**Pre-registered falsification — Wave 3 is net-negative if:** length-halts do
*not* fall, **OR** brief-rejection / plans-per-attempt *rises*. Ship only on
**fewer halts AND no rise in plans-per-attempt** — neither alone counts.

---

## What review resolved (no longer open)
- §9a ERD slice — **already implemented** (`_erd_mass_per_file`), not research.
- §9c gate-reads-prompt fear — **non-issue**: validator reads ERD/contracts from
  disk (bijection L317, mass L272, id namespace), so dropping prose from the
  prompt cannot break a gate.
- Registry count — **123**, not 116 (I dropped errors+externals; argument
  unchanged).
- Carried briefs — **not** passed to the EM: the subtree instruction states
  "id, file, depends_on only — briefs omitted deliberately" (orch:1015), and
  `carried-summary.json` is built from `subtree-scope.json['carried']`
  (orch:889), so briefs never reach the EM in subtree mode. Existing-file safety
  rests on delta + coder file-content + oracle — which is why **new-file brief
  completeness is the only real exposure**, and the new-file→full-emission
  fallback closes it.

## Guards that MUST survive (all waves)
1. Valid-id **namespace** still sent in full (names only) — never-invent-an-id.
2. **Full-emission fallback** keeps whole ERD+contracts (greenfield / lost
   `.pipeline-state`); make it *rarer* by fixing state-loss, not fatter prompts.
3. **Coverage via merge** on the subtree path (`--merge-subtree`), not via the EM
   seeing the whole inventory.
4. **D-64** driven by carried-plan DAG + node-id map, not ERD prose.
5. **New files → full emission** whenever the slice can't cover them (Wave 3).

## Verify (re-derive every claim)
```bash
cd testchat
# waves touch these; confirm the 5 EM sites + coder still carry whole-app context
grep -n '"ERD:$APPROVED/ERD.md"' scripts/orchestrate.sh          # EM sites
grep -n 'build_context "contracts:$APPROVED/contracts.json"' scripts/orchestrate.sh  # coder (654)
# the ERD slicer already exists (Wave 3 §)
sed -n '872,900p' scripts/validate-plan.py
# gate reads from disk, not prompt (bijection / mass)
grep -nE 'bijection|_erd_mass_per_file|inventory' scripts/validate-plan.py
# fast paths to widen (Wave 2)
grep -nE 'em_needed|trivial_construct' scripts/orchestrate.sh scripts/validate-plan.py
# the slice set: contracts.files == changed_files == the delta files
python3 -c "import json;d=json.load(open('scripts/.approved/contracts.json'));print('files',d['files'],'changed',d['changed_files'],'registry',sum(len(d[k]) for k in['entry_points','routes','schemas','errors','externals','ui']))"
# replay harness + corpus (Wave 1 & 3 gate)
ls -l scripts/em-bench.sh; grep -n 'ARCHIVE_DIR' scripts/orchestrate.sh
# PRD is not fed to EM/coder
grep -n 'PRD' scripts/orchestrate.sh
```
Shell caution: this is **zsh** — use `bash -c '…'` or Python for any path loop or
`\b` grep.

## Predicted impact (honest, from the earlier analysis)
- **Wave 1:** negligible time; targets H2 failure class; near-zero risk.
- **Wave 2:** **largest time win** — removes the whole ~280s EM call for the
  deltas it covers.
- **Wave 3:** small *direct* time win (~3–8% of a clean run — prefill only, and
  the EM call is generation-dominated; the prefill/decode split is **unmeasured,
  measure it**); the real payoff is *indirect* — fewer length-halt retries.
- **None of the three touches the proven-majority failure surface: TPM spec
  defects** (M31 halts 5-for-5). Set expectations accordingly — this makes minor
  milestones cheaper and the EM more reliable; it does not fix spec-tier defects.

## Constraints (standing — do not violate)
- **Coding stays local** — never route product code or this plan call to a
  frontier seat; make the pipeline proportional instead.
- Control-plane: isolated commits (one concern each), CEO/human approval,
  `.control-plane-manifest` refresh; changing *what context is sent* feeds the
  plan gate → approval-gated, not silent.
- **No invented taxonomy** — use the project's terms (delta, subtree, carried
  plan, full emission, brief, oracle, refreeze, fast path).
- Blueprint-level: land upstream (template ref `abc7f6dc2c2d`), flows to all
  children.
