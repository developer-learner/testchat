# CLAUDE.md — Master LLM Context File

> OpenCode and Claude Code can read this file via their file tools. You are
> expected to read it at the start of every session, and to consult it again
> before any action that touches the document layer (`BLUEPRINT.md`,
> `CONVENTIONS.md`, `docs/DECISIONS.md`, this file's correction log).
> Keep it current. Every correction you make to the LLM should be recorded here
> so the mistake never happens again.

---

## Project Overview

**Name:** testchat
**What it does:** A minimal chat UI between a human user and a local LLM. FastAPI backend serves a browser-based chat interface and proxies messages to any OpenAI-compatible local LLM endpoint. Built iteratively: M1 echo, M2 live LLM, M3 streaming, M4 conversation history.
**Status:** In Development

---

## Tech Stack

> Default template stack shown below. ADAPT to this project's real stack
> before first commit (see BLUEPRINT.md Rule 3).

```
Language:     Python 3.12+
Framework:    FastAPI
Database:     None (in-memory, no persistence)
Auth:         None
Hosting:      Local only
CI/CD:        GitHub Actions
Testing:      pytest
```

---

## Commands

> Feature work normally goes through the pipeline (`scripts/orchestrate.sh`),
> not manual edits — the commands below are for running and inspecting the app
> locally. Only passing frozen tests confirm success (see guardrails).

```bash
pip install -r requirements.txt            # install deps
uvicorn src.main:app --reload              # run app → http://localhost:8000

PYTHONPATH=. pytest                        # full suite (tests import `src.*`; repo root must be on the path)
PYTHONPATH=. pytest tests/test_llm_service.py::test_name   # a single test
ruff check src tests                       # lint
ruff format src tests                      # format
mypy src                                   # type-check
```

The pipeline runs the suite in an isolated sandbox as
`scripts/sandbox-run.sh --rw .cache -- pytest -p no:cacheprovider --json-report`
(with `PYTHONPATH=/work`), parsed by `scripts/orchestrate.sh`. Reproduce a
pipeline test run with `scripts/orchestrate.sh`; never mark a task done on your
own judgment.

Runtime config is via environment variables read in `src/services/llm.py`:
`LLM_ENDPOINT` (default `http://localhost:1234/v1/chat/completions`, i.e. LM
Studio), `LLM_MODEL`, `LLM_SYSTEM_PROMPT`, `LLM_TIMEOUT_SECONDS`.

---

## Application Architecture

The app is a thin FastAPI proxy in front of an OpenAI-compatible local LLM,
with a single-page browser UI. Request flow:

- **`src/main.py`** — the FastAPI app. Imports and mounts every router
  directly (no `try/except ImportError` around imports — bad imports must
  fail loudly so coder mistakes surface before tests, not as mysterious
  404s), and serves `src/static/index.html` at `/`.
- **`src/api/chat.py`** — `POST /api/v1/chat`. Validates `ChatRequest`
  (`message`, optional `model`, `history`) and returns an SSE
  `StreamingResponse` with four event types: `token`, `think` (model
  reasoning), `done`, `error`. Routes `model == "nemotron"` to a dedicated
  endpoint and returns 422 if that model isn't loaded.
- **`src/services/llm.py`** — `stream_reply()`. Streams from the LLM endpoint
  over `urllib` (no httpx dependency in the hot path), building the message
  list from history + system prompt. Splits the OpenAI delta into
  `reasoning_content` → `("think", …)` vs `content` → `("token", …)` chunks;
  every failure path collapses to a single `("error",)` tuple.
- **`src/services/models.py`** — LM Studio model discovery and nemotron
  loaded-state / endpoint routing.
- **`src/api/models.py`** — route exposing available models to the UI.
- **`src/static/index.html`** — the chat page; consumes the SSE stream.

Milestones: M1 echo → M2 live LLM → M3 streaming → M4 conversation history
→ M5 nemotron management/routing → M6 multichat in-memory threads
(see `README.md`).

---

## Project Structure

```
testchat/
├── src/                  # application source
│   ├── main.py           # FastAPI app; mounts routers, serves the chat page
│   ├── api/
│   │   ├── chat.py       # POST /api/v1/chat — SSE streaming chat
│   │   └── models.py     # available-models route
│   ├── services/
│   │   ├── llm.py        # stream_reply() — OpenAI-compatible streaming client
│   │   └── models.py     # LM Studio model discovery + nemotron routing
│   └── static/
│       └── index.html    # single-page chat UI
├── tests/                # TPM-authored frozen suite (INV-1); changes only via refreeze.sh
├── docs/                 # architecture, decisions, product, TPM role, escalation
├── tasks/                # EM write lane (plan.json) + session notes + backlog
│   └── CURRENT.md        # session notes — active work, halt notes (the PRD lives in scripts/.approved/)
├── scripts/
│   ├── bootstrap.sh      # one-time setup (sets core.hooksPath)
│   ├── phase-gate.sh     # lane + integrity gate (INV-2/3, frozen spec)
│   ├── orchestrate.sh    # shell-driven task-DAG conductor (owns all procedure)
│   ├── validate-plan.py  # plan.json gate (atomicity, DAG, coverage, mapping)
│   ├── refreeze.sh       # ONLY path frozen TPM artifacts change (auto-applies when all mechanical preflights are green; no human approval step, D-121)
│   ├── check-test-surface.py  # INV-4: tests ⊆ locked surface
│   ├── schemas/          # plan / diagnosis / contracts schemas
│   └── .approved/        # frozen TPM spec: PRD, ERD, contracts, VERSION, hashes
├── .opencode/
│   └── prompts/          # agent role definitions (em/coder)
├── .githooks/            # pre-commit gate for the interactive/human path
├── .gate-paths           # configurable directories for INV-2 enforcement
├── CLAUDE.md             # this file
└── CONVENTIONS.md        # code style rules
```

---

## Code Conventions

- Always use type hints on function signatures
- Prefer functions over classes unless persistent state is needed
- Use `logging` from the standard library — never `print()`
- One responsibility per function — if it needs a comment explaining what it does, split it
- Tests live in `tests/` mirroring `src/` structure (e.g. `src/services/user.py` → `tests/services/test_user.py`)
- Tests are TPM-authored and land via `scripts/refreeze.sh` BEFORE the code they gate — never written after the fact to match an implementation
- Use `pydantic` for data validation and serialization
- Environment variables via `python-dotenv` — never hardcode secrets

---

## What NOT To Do

> These are guardrails. Do not override them without explicit human instruction.

**Code guardrails:**
- **Do not add dependencies** without asking first
- **Do not refactor files** unrelated to the current task
- **Do not change the database schema** without explicit instruction
- **Do not remove error handling** to simplify code
- **Do not use `Any` type** — be specific
- **Do not write `TODO` comments** — either implement it or raise it as a task
- **Do not use `time.sleep()`** in production code — use proper async patterns
- **Do not commit secrets** — use `.env` and ensure `.gitignore` covers it

**Pipeline guardrails (Rules 6-7, see BLUEPRINT.md; ladder details in DECISIONS.md D-26..D-32):**
- **No agent authors or edits tests** — the suite is TPM-authored, installed only via `scripts/refreeze.sh`, and hash-pinned in `scripts/.approved/frozen-manifest` (INV-1, now structural: tests are written before the code exists, by a tier that never sees the implementation).
- **Do not cross role boundaries** — Coder writes exactly the one file its task names (`phase-gate.sh task`); EM writes `tasks/` only (`phase-gate.sh em`). Enforced by read-only sandbox mounts (D-30) with the gate as backstop (INV-2).
- **Tests observe only the locked surface** — imports from `contracts.entry_points`, routes from `contracts.routes` (INV-4, checked at freeze time by `scripts/check-test-surface.py`).
- **Do not skip escalation** — retry → EM consult → brief/plan revision (bounded) → batched TPM bundle → re-freeze (gate-approved: refreeze auto-applies on green preflights, D-121). All counters shell-owned. See `docs/ESCALATION.md`.
- **Sync the stack before every freeze (D-50).** The TPM chooses the tech stack at spec time. Before running `refreeze.sh`, check the staged tests' imports against `requirements.txt` and add anything missing (this edit is in the conductor's lane). The sandbox image rebuilds itself when `requirements.txt` or `Containerfile` change — never manually delete or rebuild images.
- **TPM shuttle is a verbatim relay (D-49).** When the CEO asks for the TPM prompt/briefing: run `scripts/tpm-pack.sh` and reproduce its ENTIRE stdout in your reply, unabridged — never summarize it, never point the CEO at repo files (the bundle is assembled from several sources; it cannot be hand-collected), never claim it is "in the clipboard." When the CEO pastes a TPM reply back: write it to a temp file unmodified and run `scripts/tpm-unpack.sh <file>` — do not re-type or edit it.

**Operating guardrails (from hard-won failures — see BLUEPRINT.md):**
- **Do not set a thinking model as the active model.** Thinking models leave `content` empty and put output in `reasoning_content`, which breaks parsing. The model must be non-thinking local OR frontier.
- **CARDINAL RULE — an EM/coder failure is never re-run blind.** If an EM or coder call fails, stop and troubleshoot the root cause — read the failure message, fix the harness/context/spec — never re-run the same call expecting the model to succeed next time. One attempt per run per call; a re-run is legitimate ONLY after a root-cause fix (then exactly one clean run). Measure and test through the pipeline's own machinery (`llm-call.sh` + schema + profile budget), never a hand-rolled copy of it.
- **Do not trust your own "it works" — only passing tests confirm success.** Run `pytest`. The tests are ground truth, not your assessment. Do not mark a task done on self-judgment.
- **Do not proceed past an unreachable LM Studio or a missing service** — halt and report.
- **Do not invent product or architecture decisions to fill an ambiguous spec** — that is the human's job. Halt and ask.
- **Do not run destructive commands** (`rm -rf`, `git push --force`, drop tables, delete files outside the project) — halt and ask.

---

## Current Focus

The frozen spec (PRD/ERD/contracts + version) lives in `scripts/.approved/`;
`tasks/CURRENT.md` holds session notes and halt notes. New features start in
the TPM web chat (see `docs/TPM-ROLE.md`) and enter via `scripts/refreeze.sh`.

---

## Capability Ladder (D-27)

| Tier | Where it runs | Produces | Writes |
|------|---------------|----------|--------|
| **CEO** (human) | conversation with the conductor | business intent | — (runs no commands, D-40) |
| **TPM** (frontier LLM) | web chat (D-38) or scoped repo agent via `scripts/tpm-agent.sh` (D-39) | PRD, ERD + `contracts.json`, the test suite | nothing directly — installed via `scripts/refreeze.sh` (auto-applies on green preflights, D-121), frozen in `scripts/.approved/` + `tests/` |
| **Conductor** | any chat agent the CEO chooses (Claude Code, OpenCode's Build, or a plain shell) | status reports, script invocations | docs/session notes; denied on `tests/`, `scripts/`, `src/`, control plane (D-40) |
| **EM** (mid-tier LLM) | one HTTP completion via `scripts/llm-call.sh` (D-53) | `tasks/plan.json` (decomposition), `tasks/diagnosis.json` (consults) — the shell writes both, not the model | `tasks/**` only |
| **Coder** (local LLM) | one HTTP completion via `scripts/llm-call.sh` (D-53) | one file per task, sentinel-wrapped in the reply | that one file only (gate-enforced) |

Which actual model backs EM/coder is never recorded in this repo: the CEO
maps roles to models in `~/.config/sw-dev-blueprint/models.env` (D-53,
succeeding D-41's `opencode.json` mapping). The blueprint constrains model
*class* only (frontier / mid / local non-thinking), never model identity.
No mapping for a role is a hard halt, never a silent substitution.

Tests are **run by the shell** (`pytest --json-report`, parsed by
`scripts/orchestrate.sh`) — there is no test agent. The shell orchestrator is
the only actor with procedural authority: it validates the plan, walks the
DAG, runs gates and acceptance, owns all state and escalation counters
(D-26). The EM advises at exactly two shell-initiated points; it never drives.
Neither EM nor coder has any tool or filesystem access — the orchestrator
gathers whatever context a call needs into the prompt and writes the reply to
disk itself (D-53); there is no agent harness in the execution loop at all,
only in the CEO-facing conductor seat, which never touches trusted state.

**The loop (all steps conductor-driven; the CEO only talks):**
TPM spec frozen (`refreeze.sh` — applies automatically when every
mechanical preflight is green, D-95/D-121; `--diff` shows a read-only
preview) → `scripts/orchestrate.sh` → EM emits plan → validated → coder
executes one task at a time → mapped frozen tests + gate after each →
delta-mapped verdict green = done (D-112; the full frozen suite is an
on-demand `--full-suite` regression check). Failures climb the escalation
ladder (`docs/ESCALATION.md`);
spec problems come back as a batched bundle for the TPM web chat and
re-enter via `refreeze.sh`.

---

## Reporting

When summarizing work since the last PM review (status reports, commit scoping, progress updates):

1. Read `docs/.pm-last-review` to get the last reviewed ref:
   ```
   LAST=$(cat docs/.pm-last-review 2>/dev/null || git rev-list --max-parents=0 HEAD)
   ```
2. Derive the commit list from the tree, not memory:
   ```
   git log "$LAST"..HEAD --oneline
   ```
3. State the scope explicitly in the report: "N new commits since reviewed ref `$LAST`".
4. Never write or advance `docs/.pm-last-review` — PM-owned.
5. If the file is missing (fresh checkout), the `git rev-list` fallback uses the initial commit — the scope becomes the entire history, which is correct for a first report.

---

## Operating Rules

> A rule that cannot be enforced mechanically is a suggestion, not a rule. Document the enforcement mechanism alongside every rule — and where there is none, say so explicitly.

Seven rules for agents working in this repo, derived from failures in prior sessions. Rules 2–7 are advisory — they rely on PM review for enforcement. Rule 1 has a mechanical backstop (see footnote).

1. **Report against the tree, never memory.** Derive your commit list from `LAST=$(cat docs/.pm-last-review); git log "$LAST"..HEAD --oneline`. State the range. A report that disagrees with `git log` is a defect regardless of the underlying work. *(Mechanical backstop: `docs/.pm-last-review` + PM source-side reconciliation.)*

2. **One commit, one concern.** Any change to a gate, invariant (INV-1/INV-2), permission, or model choice gets its own isolated commit whose message names it as such. Never bundle a constraint change with unrelated edits.

3. **A change to what a rule does is stop-and-ask.** Improving how a gate detects — fix freely. Changing what happens on a violation, or relaxing any constraint — stop and ask the PM first, even mid-run, even if the rule is what's slowing you down. The rule slowing you down is usually it working.

4. **Conditionals are checkpoints.** "Only do X if Y fails" means: when you reach that point, report whether Y failed and what you chose. If Y didn't fail, say so — don't silently act.

5. **Read the artifact, not the summary.** Report from committed files, never from another agent's summary or your own memory of a run. When source and summary disagree, source wins.

6. **"Detected" ≠ "enforced"; "nothing went wrong" ≠ "safeguard works."** Keep standalone-test results and live-run results as separate claims. An untriggered safeguard is inconclusive, not green.

7. **Decide trivial calls; escalate only contested principles.** If the PM has stated the governing principle ("put it where process docs live"), execute — don't re-ask for confirmation or surface options for a low-stakes choice. Escalate only when the principle itself is unclear, or when correctness is genuinely at stake (then asking is correct, not a failure).

---

## Key Contacts / Roles

| Role | Name |
|------|------|
| Product owner | CEO |
| Lead dev | CEO |

---

## LLM Correction Log

> When the LLM makes a mistake and you correct it, log it here.
> This is the most valuable section — it prevents repeat mistakes.
> A project 6 months in should have a rich log. That means the system is working.

| Date | Mistake | Guard Added |
|------|---------|-------------|
| 2026-08-08 | S6's whole-world-mock check shipped as a merged-suite halt — it rejected any whole-world mock in the frozen suite, not only delta-introduced ones. Its 303 selftests exercised the lint on synthetic fixtures only; nothing ran it against the LIVE frozen suite, which already carries 9 legacy bare-Mock whole-world patterns (test_models_api.py:140/166/319, test_models_service.py:159/181/190/202/214/357 — found by the reviewing session's live probe, not by me). As shipped it would have halted EVERY refreeze (AC-42, any milestone) until all 9 were re-cut — the gate blocking the very pipeline it exists to guard. | Fix landed same day (D-128 amend): check 1 is scoped to delta-touched tests only (D-116 changed-test seam) — the 9 legacy carried mocks are grandfathered, a STAGED whole-world mock in the delta is still rejected, and the standalone invocation still audits the whole suite. 304 selftests pin both directions. Meta-rule: the moment a refreeze gate is wired, run it against the LIVE suite it gates before declaring it shipped — "fixture-green" proves the mechanism, only the live suite proves it will not halt the next real freeze (Rule 6, applied to the gate itself). |
| 2026-08-08 | Two collation errors corrected before code changed. (1) The session review's "build" list included the post-condition lint (P1, S4) — but `check-ac-postconditions.py` (the S4 pre-check) already ships and is wired into `refreeze.sh`; a backlog-shaped review that never reads the artifact list describes a shipped gate as missing. (2) The changed-tests-first ordering was mislabeled "conductor-cheap": it needs `pytest_collection_modifyitems` in `tests/conftest.py`, which is hash-pinned in `frozen-manifest` (INV-1) — TPM refreeze item, not a conductor edit (the conductor alternative is orchestrate-side reordering — a design decision, not a quick edit). | (1) Before collating any P1 as "to build", grep the actual preflight list (the S-checks in refreeze.sh) and the manifests for the class's door — a gate that exists makes it a verification task, not a build task. (2) Assignability is a property of where the artifact lives: a file hash-pinned or TPM-authored (INV-1) can only change via refreeze — check the lane of the file itself before labeling work "conductor-cheap". |
| 2026-08-07 | The D-126 metrics layer (mirrored from the blueprint the same day) was built to write `.pipeline-state/logs/metrics.tsv` and read that dir's timings.tsv/run-exit.log — but the success teardown `rm -rf .pipeline-state` (orchestrate.sh) wipes exactly those files, so the row could never accumulate the ≥3 rows D-115's admission rule needs; the milestone's own data died with it. That is D-108 verbatim ("proving that erased state was safe to erase is not the same as preserving the durable facts the next phase still needs") despite the lesson sitting in this log and the durable pattern already existing — `.em-archive/` and `.measurement/` were placed OUTSIDE the blast radius on purpose, and the metrics sink went inside it anyway. The defect passed 299 selftests because the tests built their own substrate inside `.pipeline-state`, reproducing the defect. | D-126 amended same day (blueprint `a670078` → this repo via template update): `metrics-report.py` reads ONLY durable sources (`.measurement/counters` rows with rc/spec/elapsed, `.measurement/timings-*.tsv` copies, spec-tagged `.em-archive` metas, the committed flake ledger) and writes `.measurement/metrics.tsv`; the success path records the row automatically after the `[success]` commit with `|| true` (report-only, never fails a run). Selftests rebuilt to build NO `.pipeline-state` at all — the durability property is now the fixture (plus a spec-scoping test). Meta-rule: a derived-data sink that must accumulate across milestones lives OUTSIDE `.pipeline-state` and is sourced from what survives the success teardown; a selftest that builds its own substrate inside the wiped dir tests nothing. |
| 2026-08-07 | A full review found the DECISIONS.md ledgers had silently diverged between this repo and the blueprint: the completion-criterion decision lived only here (as D-112), while the blueprint's D-112/D-116/D-117 numbered different decisions (container builds / node-id relabel / suite size-governance) — yet every blueprint doc cited "D-112" as the criterion. The ledger has no mechanical drift check (DECISIONS.md is in no manifest), and back-porting code without its decision records is invisible drift. | Ledger alignment executed 2026-08-07 in both repos (blueprint `71d7404`): this repo back-ported D-108..D-111, D-113..D-115, D-123..D-125 from the blueprint; the blueprint renumbered its three conflicting entries and back-ported this repo's D-112/D-116..D-120/D-122. Both ledgers now agree number-for-number. Guard rule: any control-plane back-port commit must carry its DECISIONS entries in the same operation — code and ledger travel together. |
| 2026-08-06 | M35 plan gate: the EM (qwen3.6-27b) failed the plan ask twice identically — mis-placed Playwright test node-ids on T1 instead of the DAG's final task (D-64) and invented contract ids (contract-repair dropped them). Root cause analysis with the CEO: the EM prompt demanded THREE jobs — sequencing (lite), per-file coder brief authoring (real engineering load; the coder sees only the brief), and interpreting a DETERMINISTIC placement rule (a mechanical rule delegated to a model). The 27b sits below the ~32B constraint-density line; both failures were composition-density, not reasoning. CEO ruling: EM = coder management only; TPM (frontier) owns everything else. | Redesigned, committed as `f21e47c`: (1) D-64 placement is now GATE-OWNED — validate-plan.py auto-moves browser node-ids to the final task and writes the correction back to plan.json; the rule left all three EM prompt surfaces (orchestrate.sh full-plan + delta-replan, em.md). (2) ERD-DELTA v82 now carries the TPM-authored Task DAG (T1/T2 + depends_on) and VERBATIM coder briefs — the EM copies, it does not compose; a `brief_wrong` verdict therefore routes back to the TPM as a batched bundle, not a mid-run EM rewrite. EM residue = transcription + one diagnosis verdict. Rule: deterministic rules belong in gates, not prompts; brief-authoring load belongs at the tier that authors the spec. |
| 2026-08-06 | M35 v82 run + post-run analysis, two layers: (1) MY TPM defect: the two AC-153 tests never selected a model, and the app's submit guard returns "Pick a model" when the selector is empty — so Ctrl/Cmd+Enter never produced a message bubble and both tests were genuinely red (5/7 of the M35 node-ids passed). The conductor's run never even ran the tests: T2's two escalations were coder-CALL failures (empty content / "=== NO CHANGES ===" — the pipeline re-executing already-done work), and the EM's "LLM provider outage" verdict was right for that evidence. (2) The SYSTEMIC defect, exposed by asking "would any gate have caught this": per-task placement was PROSE, interpreted by the EM (not data the gate derives from); the empty-tests invariant was satisfied by a VACUOUS smoke check (`grep -q webToggle && pollStatus && queueRender` — three pre-existing symbols, green on the untouched file, so T1 accepted with zero evidence); the fallback observer was blind (the app.js smoke greps pre-existing symbols). | Fixed, committed as `3baeb53` + `8eeaeae`, staged as spec v83: (1) `contracts.test_mapping` is now frozen DATA pinning every delta node-id to its behavioral-owner file; validate-plan.py auto-places each pinned node-id at the task owning its file, wherever the EM mapped it (D-64 survives only as the fallback for unpinned browser node-ids); check-spec-delta.py rejects mapping keys that aren't frozen node-ids and targets outside contracts.files. (2) refreeze.sh now requires NEW/CHANGED smoke checks to be RED on the current tree (D-65 no_edit exempt; re-freezes over an already-implemented tree warn via the D-75 marker) — a check that passes pre-implementation gates nothing. (3) The two AC-153 tests select `beta-model` before pressing the shortcut (suite-consistent; verified 7/7 in the sandbox). RULES: (a) behavioral-ownership mapping belongs in frozen data, not prose; (b) an acceptance signal that is green before the milestone runs is no signal — red-before-green applies to smoke checks as much as tests; (c) tests change ONLY through refreeze.sh staging (a direct test-edit commit is correctly rejected by the phase-gate — the fix rides the freeze). |

| 2026-08-06 | Phase 3 replay harness bypassed `llm-call.sh` and set an arbitrary `max_tokens: 4096`: all 5 replayed EM calls died with `finish=length` (archived plan replies were 6–7k tokens). The pipeline had already solved this exact class (M11a output cap, M17 budget tightening, llm-call.sh default 8192 + per-call SWBP_MAX_OUTPUT) — the harness just went around it. CEO ruling on hearing this: an EM/coder failure is never re-run blind. | **CARDINAL RULE:** never re-run a failed EM/coder call expecting a different result — halt, read the failure message, fix the root cause (harness/context/spec), then exactly one clean run. Any replay that measures model calls goes through `llm-call.sh` (schema + fence-strip + profile budget), never a raw reimplementation with a hand-set cap. |
| 2026-08-06 | M35 (Ctrl+Enter) scope claim: said "10 frozen tests pin Enter-to-send" off a grep count. Site-by-site classification shows only **1 of 10** presses Enter on message-input (test_ui.py:956, the no-model guidance test); the other 9 are Enter-commits on the rename inputs (`thread-rename-input` / `current-thread-title-input`, AC-114) that must NOT change. A pattern-match count is not a classification — the same keypress means "send" on one element and "commit rename" on another. | Verify scope claims site-by-site (which element, which handler, which AC) before stating them; when a grep count spans heterogeneous targets, report the classification, not the count. |
| 2026-08-06 | Shared-dir state check truncated with `head -3` before reusing `.tpm/outbox/`: missed a pre-existing `tests/` subdir with 4 stale Aug-2 files. They rode into the conductor's refreeze diff as phantom "bundle content" (M34 refinements + AC-154 eviction string misattributed to my bundle) and overwrote the working-tree `tests/` via the sync step. | Verify shared/staging dirs with FULL listings (no `head` truncation) before reuse; state checks must be complete reads, and every file that will be staged must be an artifact you authored or explicitly adopted. |
| 2026-08-06 | Freeze contamination: 4 stale Aug-2 test artifacts (abandoned M34-era draft) rode the v80 refreeze (af49b99) outside the declared delta (app.js + index.html only). Effects frozen into v80: AC-151 schema-acceptance coverage REMOVED from test_models_service.py (0 refs vs v79's 1), undocumented test_ui_model_0731.py (+81 lines, no v79 lineage), and an "AC-154" eviction assertion colliding with M35's AC-154. Root cause: TPM state check truncated with `head -3` (see prior entry) + refreeze stages whole outbox + conductor approval read stale files as intentional bundle content. | A freeze is valid only if its content matches the declared delta scope; any staged file without a delta story is a defect, not a refinement. Approval must be of content you can attribute, not of plausible-looking diffs. When a freeze carries spec-tier coverage loss (frozen AC without its acceptance test), correct the freeze before running — do not run and log. |
| 2026-08-06 | Wave 1 (`d9f8536`, six task keys verbatim) injected `$EM_TASK_KEYS` into `ensure_plan`'s prompt in orchestrate.sh but never defined it in drive-plan.sh's env-mirror — drive-plan.sh extracts `ensure_plan` from orchestrate.sh at run time (anti-drift design) and runs with `set -u`, so all four drive-plan selftests (spec-defect / exhaustion / first-emit / subtree) died with `EM_TASK_KEYS: unbound variable` from the moment Wave 1 landed. The regression sat red in testchat, blueprint, and linkbox for two days — and two full-suite runs mislabeled those failures as "pre-existing environment-dependent": a `git stash` clean-tree check had proven only the working-tree delta innocent, which it did, while the committed baseline stayed guilty. Classification was by test name and history, never by the failure message. | Fixed (`a9541e4` testchat / `2011ed2` blueprint / `65341f5` linkbox): drive-plan.sh now extracts `EM_TASK_KEYS` from orchestrate.sh with the same sed anti-drift pattern as its function extraction, failing loudly on shape change. Meta-rule: a stash-based "pre-existing" check proves the *delta* innocent, never the *baseline* — for any failing test, read the failure cause (the message), not the name or the history, before calling it environmental; and run the full selftest suite after any control-plane change, since the suite is the template's own gate (a regression can sit greenless for days otherwise). |
| 2026-08-03 | The M33 close-out run (spec v77) was meant only to commit \`[success]\` on an already-green milestone (192/192 host), but instead re-executed three completed tasks (T2/T3/T4) and burned T4's full attempt+revision budget failing the frozen oracle — ~25 min and four coder calls for work already done. Not a coder or ladder fault; two composed spec-layer defects: (1) DELTA-v77's \`changed_tests\` carried ~50 byte-identical restaged UI tests (the M31-era spec-only-delta workaround), so subtree invalidation correctly saw complete tasks as hit and re-ran them; (2) the plan briefs were stale v74 artifacts — T4's brief mandated installing BOTH \`data.threads\` and \`data.revision\` at startup hydration, but the implementation that actually passes the oracle (\`d2661bf\`) installs only the revision. Brief and oracle disagreed; the coder faithfully built the brief and the oracle rejected it twice. | Resolved as spec-defect, no code owed: reverted both T4 attempts (\`53289d6\`, \`cd7f756\`) to the proven-green tree, kept T2's independently-green edit, closed out manually per the M28 precedent. Structural guard (already queued): the v78 consolidation refreeze retires the accumulated delta stack and resets scope, and D-107's retire-on-refresh collapses the stale briefs — both root causes are the palimpsest the consolidation removes. Meta-rule: a \`plan.json\` outlives the spec versions that shaped it; once a delta stack accumulates restaged carries, any re-run re-executes finished work and chases a superseded directive — consolidate to a standing ERD before the stack ages, and never trust a plan brief older than the current oracle. |
| 2026-08-02 | M33 T2 v77: coder wrote \`from fastapi import JSONResponse\` (JSONResponse lives in \`fastapi.responses\`), and passed raw Pydantic \`payload.threads\` to \`save_versioned_snapshot\` where the pre-coder call site had done \`[t.model_dump(exclude_none=True) for t in payload.threads]\`. First bug: import raised ImportError, \`src/main.py\`'s defensive \`try/except ImportError\` router-mount swallowed it, every \`/api/v1/threads\` request returned 404. Second bug: json.dump could not serialize Pydantic objects. Four coders (deepseek-0731 thinking, MTPLX qwen, LM Studio qwen, frontier) all replied NO CHANGES on the second miss — the file structurally satisfies the brief and coders do not run code. Landed as \`[live-fix, CEO session]\`. | Two changes: (1) removed the \`try/except ImportError\` wrappers from \`src/main.py\` — bad imports must fail loudly so coder mistakes surface before tests, not as mysterious 404s. (2) ERD/brief improvement rule (TPM-side): whenever an ERD or brief names a Python type by identifier, also name its import path; whenever a function-call boundary crosses between typed models and dicts, spell out the conversion at the call site. Both are cheap, both would have caught this class of failure in-brief without adding to coder ceremony. |
| 2026-07-28 | M32 had correct PRD/tests from v67 but stale ERD implementation guidance through v70, so repeated EM attempts planned the wrong behavior. At v71 the validator enforced D-64 without the EM prompt stating it. Six removed UI lines and one replacement took five spec versions to reach a coder that passed both tasks first try. | D-107 makes `ERD-DELTA.md` mandatory for behavioral freezes, validates its sections plus new AC/file coverage, makes it authoritative to the EM, and retires it when a later standing-ERD refresh consolidates the completed milestone. Validator-only D-64 and empty-contract-list rules now appear verbatim in both EM prompt surfaces. |
| 2026-06-04 | Table-driven "fill in the blanks" missed files not in the table; `[NAME]` survived. | Use a placeholder-shaped grep as the verification gate — never rely on a maintained list for completeness. |
| 2026-06-04 | Feature-complete had no defined end state (stale CURRENT.md, open backlog, "active development" voice). | Add a Project Completion / Maintenance Transition section with a checklist and curated cleanup step. |
| 2026-06-04 | Bootstrap expected user to run scripts and opencode manually; no agent-driven path from URL + name alone. | Agent-driven flow: create, read, spec-or-ask, adapt, fill, grep-gate, commit — user runs nothing. |
| 2026-06-04 | Aider→OpenCode migration left 3 cosmetic Aider references and never created the AGENTS.md symlink that docs already advertised. | After any agent/CLI migration commit, grep for old-tool residue and verify every doc-claimed filename with `ls` / `git ls-files`. |
| 2026-06-04 | BLUEPRINT.md bloated to 557 lines through redundancy (duplicate sections, restated rules, repeated slogans). | Target ≤450 lines [demoted — see DECISIONS.md]. After any doc edit, verify every `Step N` reference reaches a `### Step N` heading. The unit of quality is clarity, not column count. |
| 2026-06-04 | OpenCode did not pre-load AGENTS.md; auto-load claim was false. Model fetched content via tool but answered wrong. | Memory layer is best-effort, not enforced. For must-hold rules, prefer mechanical gates (grep, `wc -l`, CI, hooks) over doc guards. |
| 2026-06-04 | Added a BLUEPRINT.md date-specific project guard to CLAUDE.md template, muddying template-vs-project boundary. | Template files hold generic guards; project-specific rules live in DECISIONS.md and the correction log. Cross-reference, don't copy. |
| 2026-06-30 | A derived project (spark) discovered via real build-plan runs that a local coder-class Build model handled atomic single-file tasks perfectly but silently dropped half of a multi-file task and stalled on a genuinely ambiguous CLI instruction — the template's architect prompt had no guidance for briefing a strong-coder/weak-agent local model. The fix lived only in the derived project until ported back here. | Added BLUEPRINT.md Rule 8 (brief Build as a precision tool: atomic tasks, no negative-constraint framing, split multi-file tasks, end every brief with an explicit self-verify step) and the matching clause in `.opencode/prompts/architect.md`. Update `scripts/.control-plane-manifest` after any further edit to that prompt file. |
| 2026-06-30 | `scripts/.control-plane-manifest` had stale hashes for `build.md`/`test.md`/`pm.md` left over from commit `3639742` (role-boundary guard added to all four prompts), which never regenerated the manifest — silent drift, only caught while porting the Rule 8 change above. | Whenever editing any control-plane file, regenerate and verify every entry in the manifest, not just the one just touched — a per-file loop diffing `shasum -a 256` against the manifest, run after any control-plane edit. |
| 2026-07-19 | M28 (spec v54) final full-suite tripped the SPEC DRIFT halt on `tests/test_ui.py::test_thinking_placeholder_shows_then_clears` — an M9-era Playwright timing test (3s SLOWPING hold) unrelated to the M28 delta (catalog UI / eject / modals). Same suite passed 150/150 in one earlier full run this session and passed 1/1 in isolation, so the halt was a flaky carried-forward test, not real drift. CEO-authorized manual `[success]` commit (69708e4) after 3 orchestrate retries all failed on the same node-id; the failing test's owning file (`src/static/app.js` behavior for AC-42) had no code change in the M28 delta. Documented in `tasks/CURRENT.md` "Results (M28 spec v54, manual close-out)". | Before manual bypass of any DRIFT halt, verify the failing node-id in isolation (`sandbox-run.sh -- pytest <nodeid>`); confirm the test's exercised file(s) are outside the delta's `contracts.files` inventory. Manual `[success]` must record: failing node-id, isolation-run outcome, delta-inventory check, CEO consent. **D-77 candidate (partially landed):** `orchestrate.sh` retries a full-suite failure in isolation N times before declaring DRIFT — a real drift reproduces, a flake does not — and skips the drift path if the failing test's file is not in `contracts.files`. The isolation half landed as D-77 (2026-08-03); the verdict half is superseded by D-112 (2026-08-06): milestone completion = the delta's mapped tests only, the full suite is an on-demand `--full-suite` check, and unrelated failures never halt a milestone. |
| 2026-07-25 | Three defects confirmed live (unload never verifies the process died; a locked thread pinned to an unloaded model is a dead end; documented run command collides with ds4-server on 8000). None were test-discipline failures — the tests faithfully encode ACs that specify *mechanisms* instead of *outcomes*. AC-95 says "SIGINT the process and return `{status:unloaded}`", never "the model is no longer running"; the unload test asserts `send_signal` on a `MagicMock`, which cannot fail. A lint across 77 reconstructed ACs found the flaw confined entirely to process lifecycle (5 of 8 fail) while file lifecycle passes 9 of 9 — AC-35 says "persist *such that a subsequent GET returns the updated thread*". Also found: AC-7×AC-8 leave "reachable but untracked" undefined (exactly the post-restart state), and AC-15 ("refresh unlocks the selector") was orphaned by M8 and is now contradicted by a frozen test asserting `to_be_disabled()`. See `project-trail/2026-07-25-unload-spec-lint.md`. | **Spec lint at refreeze:** any AC whose verb changes resource state (spawn/terminate/kill/unload/evict/delete/release/clear/cancel) MUST carry a post-condition clause naming an observable check ("such that <probe> fails"), not just the action. Mechanically greppable. Second gate: every delta must list the ACs it supersedes, diffed against ACs whose behavior the staged tests touch — a staged test may not contradict a live, un-retired AC. |
| 2026-07-26 | M29 shipped `psutil.net_connections()` (module-level) for port→PID discovery. It passed 153/153 in the sandbox and failed 5 tests on the macOS host: the container runs as **root**, the app runs unprivileged, and that call needs root on macOS. The frozen oracle was green over a production path that could never work — caught only because the suite was re-run on the host by hand. The per-process form (`psutil.process_iter()` → `proc.net_connections()`, skipping `AccessDenied`) works in both and is what landed. | **The sandbox is more privileged than production; a green sandbox is not a green app.** For any code whose behavior depends on a capability (privilege, OS, an installed binary), re-run the suite on the host before declaring success. Backlog carries the structural fix: drop root in `sandbox-run.sh`. Also note the container is `python:3.12-slim` + `git ca-certificates tar` — no `lsof`, so tooling assumptions must be checked against the image, not the laptop. |
| 2026-07-26 | `.pipeline-state/tasks/` had lost its per-task `done` markers (gitignored, unversioned, and twice now partially deleted under this tree). Orchestrate cannot tell "state lost" from "greenfield repo", so the EM planned all 12 files with every task `pending`, and `contracts.no_edit_files` protected only 3 — the coder was about to be handed `app.js`, `chat.py`, `threads.py`, `index.html`, `websearch.py`, none of which the delta touched. Caught by reading the plan before the first coder call; **no gate would have stopped it**. | Two mechanical fixes, both now applied: `no_edit_files` is derived and **inverted** (a file not named by the delta is untouchable, rather than fair game), and orchestrate **fails closed** when task-state is empty while `src/` is populated. The general rule: absence of state must read as *unknown*, never as *nothing to do* — fail-open defaults are silent. |
| 2026-07-26 | The M29 `psutil` dependency broke CI on `Library stubs not installed for "psutil"` after passing two full platform runs at 153/153. `mypy` is listed in this file's commands but nothing local runs it — the sandbox acceptance is pytest + ruff only, so type-checking existed **solely** as a CI gate. | Any gate that exists only in CI will be discovered by a red build. Fold `mypy --explicit-package-bases src/` into the sandbox acceptance so local and CI verdicts cannot diverge (filed in `tasks/BACKLOG.md`). When adding a dependency, add its stubs package in the same commit. |
