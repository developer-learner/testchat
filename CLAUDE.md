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

### Adding another local LLM (one-time config, no code, no milestone)

The chat core is wrapper-agnostic: anything serving an OpenAI-compatible
`/v1/chat/completions` (Ollama 11434, LM Studio 1234, llama.cpp 8080,
vLLM, the script-model servers 8600/8000/8005, custom GitHub runtimes
serving that shape) works with zero code change. Procedure:

1. Confirm the wrapper is running and answers `GET <base>/v1/models` (the
   readiness contract the loader itself probes).
2. Set `LLM_ENDPOINT=<base>/v1/chat/completions` and
   `LLM_MODEL=<model name the wrapper recognizes>`.
3. Restart the app; verify with one chat request to `/api/v1/chat`.

The script-model loader (`src/services/models.py`) is only process
lifecycle (spawn / ready-probe / terminate) on top of that universal
contract — a model loaded via the loader and one launched by the wrapper's
own command line are equivalent for chat. A wrapper serving a NON-OpenAI
API is the only case that needs real code (a shim), never a milestone.

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
- **TPM/milestone runs are inform-first (D-139).** Diagnosing a fix as needing a TPM round-trip or a milestone (orchestrate) run is NOT a launch: stop and ask the CEO — including who will take the TPM seat. The seat may be a web-chat model, a `scripts/tpm-agent.sh` agent, or the same LLM already on the job, by the CEO's assignment; never assume "the TPM is someone else" or that the run proceeds on an agent's judgment alone.

**Operating guardrails (from hard-won failures — see BLUEPRINT.md):**
- **Do not set a thinking model as the active model.** Thinking models leave `content` empty and put output in `reasoning_content`, which breaks parsing. The model must be non-thinking local OR frontier.
- **CARDINAL RULE — an EM/coder failure is never re-run blind.** If an EM or coder call fails, stop and troubleshoot the root cause — read the failure message, fix the harness/context/spec — never re-run the same call expecting the model to succeed next time. One attempt per run per call; a re-run is legitimate ONLY after a root-cause fix (then exactly one clean run). Measure and test through the pipeline's own machinery (`llm-call.sh` + schema + profile budget), never a hand-rolled copy of it.
- **Do not trust your own "it works" — only passing tests confirm success.** Run `pytest`. The tests are binding automated completion evidence, not your assessment. Do not mark a task done on self-judgment.
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
| **TPM** (CEO-assigned seat, D-139) | web chat (D-38), scoped repo agent via `scripts/tpm-agent.sh` (D-39), or the same LLM already on the job — the CEO names the holder per session | PRD, ERD + `contracts.json`, the test suite | nothing directly — installed via `scripts/refreeze.sh` (auto-applies on green preflights, D-121), frozen in `scripts/.approved/` + `tests/` |
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
spec problems come back as a batched bundle for the TPM seat and
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
| 2026-09-02 | Two findings from the CEO's review of the T8/router incident. (1) **The root cause preceded the routing miss:** the T3 wrong-brief chain began when **v115 dropped the `## Coder briefs (verbatim)` section** that v107–v113 had carried. D-107 / M35 (`f21e47c`) established TPM-authored verbatim briefs for subtle tasks precisely because the 27B EM composes wrong briefs below the constraint-density line. With no verbatim brief, the EM composed T3's as "put the not-ready re-probe in the exception handler" — the wrong path (the 404 race arrives as a message-less `("error",)` item in the stream loop, never a raised exception). The originating defect was a spec-authoring lapse — an existing mechanism dropped — not the coder or the model. (2) **Framing/deflection in my own reporting:** I then offered the fixes — route small changes direct (D-132), consolidate before the stack bloats (D-107 retire-on-refresh + the 2026-08-03 lesson), keep verbatim briefs — as "levers for smoother future updates," which frames them as process gaps to close. All three already exist in the blueprint; every failure was a failure to APPLY them (the routing one mine, this session). Labeling my own application-misses as systemic improvements softens accountability and aims future effort at building what already exists. | (1) A behavioral delta with any non-trivial control-flow or placement decision carries a TPM-authored `## Coder briefs (verbatim)` brief for that task — never left to EM composition (D-107 restated). A dropped verbatim brief on a subtle task is the first thing to look for when a coder "faithfully builds the wrong thing." (2) Reporting discipline: before offering any fix as a "lever / improvement / what would make this smoother," grep `docs/DECISIONS.md` + this log for the mechanism. If it already exists, name it as an application/discipline failure (and whose), not a systemic gap — a rule already in the log presented as a new improvement is a misattribution that hides the real miss. Meta-rule: the process usually already has the answer; when it does, the honest finding is "not applied," never "missing." |
| 2026-09-02 | When T8's T3 task escalated (caps-exhausted — the EM-composed brief pointed the coder at the wrong code path), I stayed in milestone-mode and authored a v116 brief-only refreeze + re-ran `orchestrate` to fix it. But the T3 fix was one file (`src/api/chat.py`), ~10 lines, fully deterministic, and its frozen tests already existed and passed — a textbook D-132 direct-fix candidate. Running it through the full pipeline instead resolved the delta baseline to v105, dragged in the whole v106–v119 delta stack (122 KB EM planning context vs the 65 KB budget), and hit a plan-gate halt on a stale UI file (`catalog.js`) unrelated to the fix — friction caused entirely by the routing choice, not the change. I even cited D-132 correctly ("textbook go-direct candidate") in later analysis, so the rule was known and recited, just not applied at the decision point. Same class as 2026-08-10: I routed on the mechanism-label ("a frozen brief is wrong → frozen artifacts change via refreeze") instead of the property that decides (size + determinism). The fix ultimately landed direct (`66c64fb`, chat.py only, 6/6 router tests green in the sandbox); the milestone (v119) then closed out on its own evidence. | The milestone-vs-direct routing decision is a checkpoint that fires the moment a task fails/escalates, BEFORE continuing the current lane — re-evaluate on size + determinism, never on the pipeline's next mechanical step. An escalation bundle says "→ TPM"; the in-track reflex "→ refreeze" is locally correct inside the pipeline and globally wrong when the fix should not be on the pipeline at all. A frozen brief being wrong does NOT force a refreeze when the fix is small, deterministic, and its frozen tests already exist and pass — land it direct (D-132), which touches neither the delta stack, the EM planner, nor the plan gate. Meta-rule (extends 2026-08-10): reciting a routing rule in hindsight is not applying it at the fork; the check belongs at the decision moment, and "the pipeline handed me the next step" is not a routing decision. |
| 2026-08-14 | The subtree re-plan fallback (D-91) promised "two rejected merges abandon subtree mode", but the loop increments `plan_revisions` and `SUBTREE_ATTEMPTS` in lockstep before each subtree attempt (:1444/:1446), so at the default `MAX_PLAN_REVISIONS=2` the revision-cap die at :1343 always fired before the abandon branch at :1379 could ever run — the fallback was dead code, and a twice-rejected subtree planned to halt instead of widening to full emission. | D-91 amended (2026-08-14, blueprint ledger; testchat carries the code via template sync): the FIRST rejected merge abandons subtree mode, making revision two a full-plan call within the same budget; an end-to-end drive selftest pins reply-1-rejected → reply-2-is-the-full-emission prompt with the merge rejection carried as feedback. Meta-rule: every fallback's trigger must be reachable from the same counters the cap consumes — write the arithmetic once for both paths, or the branch you think is the safety net is unreachable by construction. |
| 2026-08-14 | D-126's metrics reporter ran with `--milestone HEAD` with no proof HEAD was THIS run's `[success]` commit: the guarded commit uses `git commit ... || true`, so a failed commit (identity, hook) left HEAD on a PRIOR milestone whose subject may already match `[success] spec vN` — the row would bind a stale ref and the current milestone's row would be silently missing. | P3-5 guard in orchestrate.sh (template sync): capture the pre-commit SHA, require HEAD to advance AND the new subject to be exactly `[success] spec v$FROZEN_V`, else warn loudly and skip the row. Meta-rule: a ref-binding check must verify the ref CHANGED, not merely that it matches a pattern — subject-only matching passes against the previous commit with the same subject. |
| 2026-08-14 | Independent audit found `check-spec-delta.py`'s test_mapping pin gate comparing `contracts.test_mapping` keys to frozen `test-nodeids` by exact string equality — while the whole control plane family-matches node-ids (`_id_family` in validate-plan.py, the D-116 flicker guard, the DELTA-token match one hundred lines below it in the SAME file). Testchat v106 regenerated test-nodeids in bare form but carried forward the `[chromium]`-suffixed mapping keys, so the first behavioral freeze the v106 consolidation had not already consumed would have hard-blocked on keys the pipeline itself declares equivalent. The gate is the one place the D-116/D-124 family-as-identity convention was not applied, and an initial recommendation to "fix the data" (rewriting the frozen keys once) ignored that collection shape flips both directions between freezes. | `check-spec-delta.py` pin gate now reduces both sides to the node-id family before membership testing (mirroring `_id_family`); two selftests pin the tolerance in both directions (`name[chromium]` key ↔ bare frozen node-id, and the reverse flip). A live probe against testchat's real frozen state returns `behavioral` rc=0 where the old gate rejected. Meta-rule: when an identifier set legitimately flips representation across runs (D-116), every consumer — including validation gates — must compare on the stable family key; a gate that exact-matches a shape the producer alternates is a latent hard-fail trap, and the fix belongs in the gate, not in a one-time data rewrite that the next flip voids. |
| 2026-08-14 | D-126 moved metrics inputs outside the teardown blast radius but left their successful-run producer in the EXIT trap. The success path deleted `.pipeline-state/logs/timings.tsv`, committed, and ran the idempotent reporter before that trap fired. The timing copy was therefore impossible, and the current rc=0 counter arrived only after the milestone row had been frozen without it. Source durability did not establish producer-before-consumer ordering. | D-126 amended: one `record_measurement` producer serves both ordinary exits and success. Success calls it before teardown, marks the terminal event recorded, then runs the reporter after cleanup and commit; the EXIT trap skips the duplicate. A behavioral selftest executes capture → teardown → the real metrics reporter → trap and proves the timing survives and the current success is counted exactly once. Meta-rule: for a durable derived report, pin both where evidence lives and when its producer runs relative to every destructive step and idempotent consumer. |
| 2026-08-14 | D-147 treated PRD and ERD trimming as symmetric. The chat bundle reduced the standing PRD to a capsule with no historical AC ids, but stage 2 retrieves contract bodies only and D-136 requires any staged PRD to preserve every historical AC. A chat TPM could therefore be asked to return a complete additive PRD it had never seen. | D-147 amended same day: `tpm-pack.sh` always emits the complete frozen PRD; only the standing ERD remains summarized. Active-delta and no-delta selftests pin historical AC visibility, and the dead product-capsule generator/budget were removed. Meta-rule: trim authoritative context only when a tested retrieval or merge path can reconstruct everything the author must return. |
| 2026-08-14 | Diagnosed the Enter-key correction as needing a TPM round-trip and immediately packed the TPM bundle and prepared to relay it to the presumed "TPM web chat" — without asking the CEO whether that route was wanted, and without asking who would take the TPM seat. "The TPM is someone else" is a persona assumption, not a contract: the seat may be held by any LLM the CEO names per session, possibly the same one already on the job. Launching a TPM or milestone cycle is a process decision with human cost; informing first is the checkpoint, not ceremony. | Landed as D-139 (2026-08-14) in both ledgers (D-138 is the contract-claims decision of the parallel lane): TPM and milestone runs are CEO-gated at launch — an agent that diagnoses a fix as needing a TPM round-trip or an orchestrate run informs the CEO and asks (including who takes the TPM seat) before packing a bundle or starting a run. Swept CLAUDE.md (ladder row, guardrails), docs/DECISIONS.md, docs/TPM-ROLE.md, docs/CEO-PLAYBOOK.md, docs/ESCALATION.md, docs/TESTING.md, README.md, and the `tpm-pack.sh`/`tpm-agent.sh` headers; manifests re-pinned. Meta-rule: a route decision (who holds which seat, whether to launch) is a human call at the moment it is made — the mechanism docs define HOW a seat works, never WHO holds it per session. |
| 2026-08-10 | Described the cloud LLM lane's hermetic environment in its allocation blurb with three overstatements, corrected by the lane itself during closeout: (1) said toolchains are "pre-installed" — actually pytest/fastapi are missing on entry (`pip install -r requirements.txt` first), and the browser toolchain differs from host/CI (container Chromium build 1194 vs pinned `playwright==1.61.0` wanting build 1228; proxy blocks the download, so the lane runs playwright 1.56.0) — Playwright drafts are behaviorally accurate, not byte-identical; (2) said "verify the phase-gate green before landing" — the pre-commit hook is NOT wired in the lane (`core.hooksPath` unset, bootstrap never ran); the lane reproduces the gate's checks by hand (regen-manifest.sh, check-test-surface.py, manifest diffing); (3) named one blind-spot category (host-only truth) — there is a second: harness-only limits (T4: `TestClient` isolates each request on its own event loop, so a stable suite-RED was unachievable; the fix shipped with an in-isolation RED/GREEN proof and an explicit "no stable frozen test; confirm on host"). | Lane allocation blurbs state: entry bootstrap (deps missing on first run), the playwright/Chromium build caveat for browser drafts, manual gate reproduction instead of the hook, and the three-mode taxonomy — host-only truth (draft but unprovable in the seal), harness-limited (draft + in-isolation RED/GREEN + explicit no-test flag, never a fabricated green), else draft-here/verify-there. "Green in the seal proves the code; only the host proves the environment" extends to: a test that cannot be made RED in the harness is labeled as such, not invented. |
| 2026-08-10 | Recorded the 2026-08-09 CEO routing ruling in `tasks/CURRENT.md` on the bug/feature axis ("the VM + EM/coder + sandbox are for milestone feature runs ONLY, not ad-hoc bug fixes; bug fixes now go direct") without pushing back on the property that actually decides. The label is packaging, not size: v99 was a bug fix that correctly rode the pipeline and sailed green (multi-file, cross-layer, AC authoring); the model-management bundle was also a bug fix that died in the pipeline for spec-authoring defects a direct read would have caught, costing three freezes before shipping direct as `7bfc622`. A ruling written down on the wrong axis becomes the standing rule until someone corrects it. | Routing decisions are documented by the property that decides — size and determinism — never the bug/feature label, and the axis is verified against the incident record before it is committed to session notes or a ledger. Landed as D-132 (2026-08-10) in both DECISIONS.md ledgers; supersedes the CURRENT.md ruling. |
| 2026-08-10 | During the check-drift episode I popped `stash@{0}` ("stale plan.json from interrupted M35 run") to test a baseline hypothesis without inspecting its contents. The stash carried halted-run versions of THREE files — `src/services/models.py`, `tests/test_model_lifecycle.py`, `tests/test_models_api.py` — alongside plan.json, and its application silently overwrote the committed direct-fix (`7bfc622`) versions in the working tree. If I had committed the next staged change blindly, the fix would have been reverted; caught only because `git status` showed unexpected modified files. | A stash is an unlabeled full working-tree snapshot, not a single named file — before popping any stash, inspect its file list (`git stash show --name-only`) and its diff, and only apply it over a HEAD whose content it could plausibly supersede. After ANY stash operation, diff the working tree against HEAD before committing. Stashes from interrupted runs whose files were subsequently committed by newer work are debris, not context — drop them once their origin run is formally closed. |
| 2026-08-08 | Claimed the shipped search feature was "title-only" — the sidebar filter matches ONLY thread titles — when answering the CEO about the "Search across threads" backlog entry. The claim was inferred from the M18 test (which asserts the title path) and the PRD grep, without reading the implementation. `src/static/threads.js:374-377` matches BOTH thread titles AND message content (`thread.messages[m].content.toLowerCase().includes(threadSearchQuery)`), so the CEO's described behavior ("type zebra → every thread containing the term stays in the sidebar → open it → hits highlighted") was exactly what ships. A wrong feature-scope claim can retire a backlog item incorrectly or greenlight duplicated work. | Feature-scope claims about shipped behavior are verified against the IMPLEMENTATION (and its tests for the behavior's seams), never generalized from one test's assertion path: when a test only exercises one match route, say "the test pins the title route" — do not state the feature as a whole. Re-verify delivered-feature claims the same way before retiring product backlog items. |
| 2026-08-08 | Asked the CEO a technical scope question ("AC-42 only or bundle all three?") — the process-seat's own call, presented to the CEO as an open menu. CEO reads cost and intent only; technical scope (what to recut, how much to bundle) is the TPM's seat. | CEO gets decisions with numbers, never technical menus: "AC-42 alone ~5 min; all three ~45 min — decide on the cost." Scope questions are decided by the technical seats and only *presented* (with cost) when they have cost/time/resource impact. Logged in docs/CEO-PLAYBOOK.md under "Rules that keep you safe". |
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
