# Findings for sw-dev-blueprint — from testchat M31, 2026-07-26

**Source:** testchat M31 ("current-chat awareness"), specs v61→v63, one full
orchestrate run on the mlx-serve 4-bit seat.
**Status:** milestone NOT built. Three TPM-authored spec defects consumed three
refreeze cycles and ~90 minutes. All three were mechanically detectable at
freeze time with tools already in the repo.
**Purpose:** evidence for blueprint gate/design changes. Filed project-side per
the standing rule that incident records stay with the child; carry across
whatever is useful.

Every claim below was verified against the tree during the session; file and
line references are to testchat at spec v63 (`7d756d0`).

---

## Evidence — where a run's wall clock actually goes

Complete phase timing, Run A (mlx-serve 4-bit, `SWBP_RUN_BUDGET=3600`):

| Phase | Time | Share |
|---|---|---|
| **EM plan call** (1 call, validated first try) | **282s** | **68%** |
| EM diagnosis calls (2) | 62s | 15% |
| Acceptance runs (7, incl. all no-edit tasks) | 42s | 10% |
| Coder call (1 file, diff-based) | 15s | 4% |
| Pre-flight, gates, commits | ~12s | 3% |
| **Total to halt** | **413s** | |

Historical EM plan calls on the same seat: 247s, 254s, 269s, 276s, 282s —
consistently 250–280s. A plan rejected on the first attempt doubles this: spec
v61 burned 530s on two attempts before halting.

Per-acceptance detail (the 10% row): 1s, 17s, 1s, 1s, 1s, 19s, 2s. The two
expensive runs are the 18-node-id Playwright sets.

---

## Finding 1 — the EM re-emits the entire inventory every run (68% of wall clock)

**Observed.** The EM produced a 13-task plan, 19,572 chars, when the delta
touched three tasks. `orchestrate.sh`'s plan prompt requires "exactly one task
per file in contracts.json's files array", so plan size scales with total
inventory, not with delta size. At the 4-bit seat's ~77 chars/s of output that
is ~253s of pure generation, matching the measured 282s.

This is the single largest cost in every run and it grows as any project's
inventory grows, independent of how small the milestone is.

**Complication.** Scoping the plan conflicts with D-64's plan↔inventory
bijection, which is load-bearing for the mapping gate. This is a design change,
not a patch.

**Possible directions** (for blueprint owners to weigh):
* carry forward unchanged tasks from the prior validated plan and have the EM
  emit only the affected subtree, with the shell reassembling the full plan
  before validation — preserves the bijection at the gate while shrinking the
  generated payload;
* allow a plan *diff* reply rather than a full re-emit;
* leave as-is and treat it as the cost of the bijection.

Highest-value target if only one change is made.

---

## Finding 2 — a spec-only refreeze silently empties the delta and disables the coder

**Observed.** Spec v62 changed only `contracts.json` (added one `smoke_checks`
entry). The resulting delta was completely empty:

```
DELTA-v62.json:  changed_tests: 0   changed_files: []   changed_contract_ids: []
```

Combined with the inverted no-edit default, this makes **every existing file
no-edit** — the coder is locked out of the entire codebase while the run still
reports normally. Caught only because the CEO asked for a pre-run check.

**Mechanism.**
* `refreeze.sh:527` populates `changed_tests` from the *presence of a test file
  in staging*, not from any content difference.
* `refreeze.sh:532` hardcodes `"changed_files": []`.
* `changed_contract_ids` (`refreeze.sh:394-416`) walks only `entry_points`,
  `routes`, `schemas`, `errors` — never `ui` entries.

So a delta that touches none of those three produces an empty scope.

**Discovered workaround, currently undocumented:** restage the test file
byte-identical. Presence alone repopulated `DELTA-v63.json` to 45 changed tests
and restored the scope. Nothing in the docs suggests this, and the failure is
silent in both directions.

**Proposed gate.** `refreeze.sh` should refuse (or loudly warn) when it computes
an empty delta while the current milestone is unbuilt — the same principle the
blueprint already applied in v60 for lost `.pipeline-state`: *absence of state
must read as unknown, never as nothing to do*. An empty delta is currently
read as "nothing is in scope" when it usually means "the author changed only
spec prose".

---

## Finding 3 — a new file in `contracts.files` can be unreachable, and nothing checks it

**Observed.** The spec added `src/static/current-chat.css` to the inventory.
Nothing in the project can ever load it:

* `src/static/index.html:7` carries the only `<link>`, and `index.html` was
  outside the delta scope, so the coder may not edit it;
* `src/static/style.css` is in frozen `contracts.no_edit_files`.

Had the smoke_check passed, the coder would have written a correct file that is
never loaded, and the highlight ACs would fail with no visible cause — a green
task producing dead code.

**Gap.** D-78's satisfiability preflight already proves this class of
unimplementability for `routes` and `entry_points` whose implementing file is
outside `contracts.files`. It does not cover static assets, whose "reachability"
is a reference from another file rather than an entry point.

**Proposed gate.** At freeze time, for each *new* file added to
`contracts.files` that is not an entry point: if no existing file, template, or
entry point references it, **and** the file that would have to reference it is
itself no-edit or frozen, the delta is unimplementable — reject with the same
force as D-78. Cheap to implement (a grep over the inventory), and it catches
the most expensive defect of this session.

---

## Finding 4 — delta scoping cannot reach files the EM did not map tests to

**Observed.** `delta v63 touches: T7 — every other existing file is no-edit`.
Only `app.js` was reachable. `index.html` was permanently out of scope for a
milestone that plausibly needed markup in it.

**Mechanism.** `cmd_affected` (`validate-plan.py:770`) derives the editable set
from `tests ∩ changed_tests`, `contracts ∩ changed_contract_ids`, or
`file ∈ changed_files`. Given that `changed_files` is hardcoded empty and the
contract delta ignores `ui` entries, **the EM's test-mapping is the only lever**
that decides what the coder may edit. The EM assigned 49 tests to `app.js` and 2
to `index.html`, so `index.html` became uneditable — a scoping decision made
implicitly by a mid-tier model, not by the spec author.

**Proposed change.** Let the TPM declare `changed_files` as a first-class field
in the staged delta, so a spec author can force a file into scope deliberately
instead of depending on EM judgment. The plumbing already reads the field; only
the freeze path needs to stop hardcoding it empty.

This matters beyond convenience: scope is a *safety* boundary, and it is
currently set by the least-capable actor in the loop.

---

## Finding 5 — `smoke_checks` are raw greps and are brittle by construction

**Observed.** This check failed against correct CSS:

```
grep -q '\[data-active="true"\]' src/static/current-chat.css
```

The coder wrote `[data-active='true']` — single quotes, identical CSS. The
failure consumed 4 coder strikes and 2 EM diagnosis calls (62s) and produced
the escalation that halted the run, all against a file that satisfied the spec.

**Proposed.** Guidance, and ideally a freeze-time lint: a `smoke_check` that
greps for a source token must be quoting- and whitespace-agnostic. Weaker than
a gate, but nearly free — the failure mode is a correct implementation failing a
spec-authored oracle, which is the most demoralising kind of red.

---

## What already worked — do not regress these

* **The inverted no-edit default (v60) does exactly what it claims.** Live
  evidence: `no-edit file (not touched by delta v63) — coder not invoked;
  running acceptance only`, correctly applied to 11 of 13 tasks, with a new
  (nonexistent) file still editable so it could be created.
* **D-65's "acceptance still runs for no-edit files" is cheap — keep it.**
  Measured at 42s of a 413s run (10%), and the final full frozen suite (D-28)
  makes it redundant only for *detection*, not for localisation. Not worth
  optimising; the 68% is elsewhere.
* **Worktrees are pipeline-safe.** `git worktree` checkouts ran `phase-gate.sh`
  and the podman sandbox correctly (170 tests collected) despite `.git` being a
  file rather than a directory. Useful for A/B seat comparisons.
* **Per-invocation env overrides work for seat swaps.** `llm-call.sh:43` only
  sources `models.env` when the role variable is unset, so
  `SWBP_EM_MODEL`/`SWBP_CODER_MODEL`/`SANDBOX_LLM_HOST`/`SANDBOX_LLM_PORT` can
  be exported per run. This allows seat A/B tests **without writing the
  CEO-owned `models.env`** — worth documenting as the sanctioned comparison
  method.

---

## Seat data points (for D-72)

* **mlx-serve 4-bit `ddalcu/Qwen3.6-27B-4bit-MTP-MLX-Serve` validated its plan
  on the first attempt** at spec v63 (282s). D-72's record has 4-bit violating
  the plan-mapping rule twice with validator feedback echoed back. This run does
  not reproduce that. Worth recording before treating 4-bit as the weaker
  planner.
* Its coder output was correct on the first attempt; the only failure was the
  TPM's brittle oracle.
* **Context-ceiling asymmetry worth documenting for seat selection:** the EM
  prompt measured 62,340 chars ≈ 19–20k tokens. A first-pass call fits in
  mtplx's 32768 window (~28k with `max_output` 8192), but a *revision* carries
  the previous plan and lands near ~34k — an overflow. mlx-serve's 50176 window
  is unaffected. An 8-bit seat may therefore fail on revision cycles for reasons
  unrelated to model quality.

---

## Process observation

All three spec defects were mechanically detectable before the freeze with
existing tools — `validate-plan.py` enforces the acceptance-signal rule that
v61 violated; one `grep link index.html` would have caught the unreachable
asset; inspecting `DELTA-vN.json` would have caught the empty scope. The failure
was authoring spec artifacts and freezing them without executing the checks the
pipeline would later apply.

That is the blueprint's own stated principle pointing at itself: a rule that
cannot be enforced mechanically is a suggestion. Findings 2, 3 and 5 are all
gate-shaped, and would protect any TPM occupant regardless of model class —
which is the more durable fix than expecting spec-time discipline.
