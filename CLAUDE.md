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
uvicorn src.main:app --reload --port 8080   # run app → http://localhost:8080

PYTHONPATH=. pytest                        # full suite (tests import `src.*`; repo root must be on the path)
PYTHONPATH=. pytest tests/test_llm_service.py::test_name   # a single test
ruff check src tests                       # lint
ruff format src tests                      # format
mypy src                                   # type-check
```

> **Never bind the app to port 8000, and never bind `0.0.0.0`.** Port 8000 is
> the DeepSeek script model's (`DS4_URL`, `src/services/models.py`), and the app
> spawns that server itself via `SCRIPT_MODELS[...]['command']`. If the app is on
> `0.0.0.0:8000`, loading DeepSeek makes `ds4-server` bind `127.0.0.1:8000` —
> and BSD gives the more-specific address priority, so the model server silently
> inherits `localhost:8000`. The open page keeps rendering, but every
> `/api/v1/*` call from it starts hitting the model server and returns
> `{"error": "unknown endpoint"}`: the chat dies mid-session with no error that
> points at the cause. Binding `127.0.0.1` instead makes the second bind fail
> loudly with `EADDRINUSE` rather than resolving silently. Observed 2026-07-25.

The pipeline runs the suite in an isolated sandbox as
`scripts/sandbox-run.sh --rw .cache -- pytest -p no:cacheprovider --json-report`
(with `PYTHONPATH=/work`), parsed by `scripts/orchestrate.sh`. Reproduce a
pipeline test run with `scripts/orchestrate.sh`; never mark a task done on your
own judgment.

Runtime config is via environment variables read in `src/services/llm.py`:
`LLM_ENDPOINT` (default `http://localhost:1234/v1/chat/completions`, i.e. LM
Studio), `LLM_MODEL`, `LLM_SYSTEM_PROMPT`, `LLM_TIMEOUT_SECONDS`.

Script-model endpoints are separate, in `src/services/models.py` — notably
`DS4_URL` (default `http://127.0.0.1:8000`). These are the servers the app
starts and stops on its own, so their ports are reserved: the app must not
occupy one. Port map in use: `1234` LM Studio, `8000` DeepSeek (`ds4-server`),
`8001` mtplx, `11234` mlx-serve, `8080` this app (per `.claude/launch.json`).

---

## Application Architecture

The app is a thin FastAPI proxy in front of an OpenAI-compatible local LLM,
with a single-page browser UI. Request flow:

- **`src/main.py`** — the FastAPI app. Mounts the chat and models routers
  *defensively* (`try/except ImportError`) so a partial build still boots, and
  serves `src/static/index.html` at `/`.
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
│   ├── refreeze.sh       # ONLY path frozen TPM artifacts change (human-gated: y/N or --approve <hash>, D-42)
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
- **Do not skip escalation** — retry → EM consult → brief/plan revision (bounded) → batched TPM bundle → human-approved re-freeze. All counters shell-owned. See `docs/ESCALATION.md`.
- **Sync the stack before every freeze (D-50).** The TPM chooses the tech stack at spec time. Before running `refreeze.sh`, check the staged tests' imports against `requirements.txt` and add anything missing (this edit is in the conductor's lane). The sandbox image rebuilds itself when `requirements.txt` or `Containerfile` change — never manually delete or rebuild images.
- **TPM shuttle is a verbatim relay (D-49).** When the CEO asks for the TPM prompt/briefing: run `scripts/tpm-pack.sh` and reproduce its ENTIRE stdout in your reply, unabridged — never summarize it, never point the CEO at repo files (the bundle is assembled from several sources; it cannot be hand-collected), never claim it is "in the clipboard." When the CEO pastes a TPM reply back: write it to a temp file unmodified and run `scripts/tpm-unpack.sh <file>` — do not re-type or edit it.

**Operating guardrails (from hard-won failures — see BLUEPRINT.md):**
- **Do not set a thinking model as the active model.** Thinking models leave `content` empty and put output in `reasoning_content`, which breaks parsing. The model must be non-thinking local OR frontier.
- **Do not retry the same failing fix more than twice.** Two strikes → escalate to a frontier model, or halt and leave a note.
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
| **CEO** (human) | conversation with the conductor | business intent, freeze approvals | — (runs no commands, D-40) |
| **TPM** (frontier LLM) | web chat (D-38) or scoped repo agent via `scripts/tpm-agent.sh` (D-39) | PRD, ERD + `contracts.json`, the test suite | nothing directly — installed via `scripts/refreeze.sh` (human-approved diff, D-42), frozen in `scripts/.approved/` + `tests/` |
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

**The loop (all steps conductor-driven; the CEO only talks and approves):**
TPM spec frozen (`refreeze.sh` — terminal y/N, or conductor `--diff` /
`--approve <hash>` behind the conductor's own ask-prompt, D-42) →
`scripts/orchestrate.sh` → EM emits plan → validated → coder executes one
task at a time → mapped frozen tests + gate after each → full frozen suite
green = done. Failures climb the escalation ladder (`docs/ESCALATION.md`);
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
| <!-- add rows below --> | | |
| 2026-06-04 | Table-driven "fill in the blanks" missed files not in the table; `[NAME]` survived. | Use a placeholder-shaped grep as the verification gate — never rely on a maintained list for completeness. |
| 2026-06-04 | Feature-complete had no defined end state (stale CURRENT.md, open backlog, "active development" voice). | Add a Project Completion / Maintenance Transition section with a checklist and curated cleanup step. |
| 2026-06-04 | Bootstrap expected user to run scripts and opencode manually; no agent-driven path from URL + name alone. | Agent-driven flow: create, read, spec-or-ask, adapt, fill, grep-gate, commit — user runs nothing. |
| 2026-06-04 | Aider→OpenCode migration left 3 cosmetic Aider references and never created the AGENTS.md symlink that docs already advertised. | After any agent/CLI migration commit, grep for old-tool residue and verify every doc-claimed filename with `ls` / `git ls-files`. |
| 2026-06-04 | BLUEPRINT.md bloated to 557 lines through redundancy (duplicate sections, restated rules, repeated slogans). | Target ≤450 lines [demoted — see DECISIONS.md]. After any doc edit, verify every `Step N` reference reaches a `### Step N` heading. The unit of quality is clarity, not column count. |
| 2026-06-04 | OpenCode did not pre-load AGENTS.md; auto-load claim was false. Model fetched content via tool but answered wrong. | Memory layer is best-effort, not enforced. For must-hold rules, prefer mechanical gates (grep, `wc -l`, CI, hooks) over doc guards. |
| 2026-06-04 | Added a BLUEPRINT.md date-specific project guard to CLAUDE.md template, muddying template-vs-project boundary. | Template files hold generic guards; project-specific rules live in DECISIONS.md and the correction log. Cross-reference, don't copy. |
| 2026-06-30 | A derived project (spark) discovered via real build-plan runs that a local coder-class Build model handled atomic single-file tasks perfectly but silently dropped half of a multi-file task and stalled on a genuinely ambiguous CLI instruction — the template's architect prompt had no guidance for briefing a strong-coder/weak-agent local model. The fix lived only in the derived project until ported back here. | Added BLUEPRINT.md Rule 8 (brief Build as a precision tool: atomic tasks, no negative-constraint framing, split multi-file tasks, end every brief with an explicit self-verify step) and the matching clause in `.opencode/prompts/architect.md`. Update `scripts/.control-plane-manifest` after any further edit to that prompt file. |
| 2026-06-30 | `scripts/.control-plane-manifest` had stale hashes for `build.md`/`test.md`/`pm.md` left over from commit `3639742` (role-boundary guard added to all four prompts), which never regenerated the manifest — silent drift, only caught while porting the Rule 8 change above. | Whenever editing any control-plane file, regenerate and verify every entry in the manifest, not just the one just touched — a per-file loop diffing `shasum -a 256` against the manifest, run after any control-plane edit. |
| 2026-07-19 | M28 (spec v54) final full-suite tripped the SPEC DRIFT halt on `tests/test_ui.py::test_thinking_placeholder_shows_then_clears` — an M9-era Playwright timing test (3s SLOWPING hold) unrelated to the M28 delta (catalog UI / eject / modals). Same suite passed 150/150 in one earlier full run this session and passed 1/1 in isolation, so the halt was a flaky carried-forward test, not real drift. CEO-authorized manual `[success]` commit (69708e4) after 3 orchestrate retries all failed on the same node-id; the failing test's owning file (`src/static/app.js` behavior for AC-42) had no code change in the M28 delta. Documented in `tasks/CURRENT.md` "Results (M28 spec v54, manual close-out)". | Before manual bypass of any DRIFT halt, verify the failing node-id in isolation (`sandbox-run.sh -- pytest <nodeid>`); confirm the test's exercised file(s) are outside the delta's `contracts.files` inventory. Manual `[success]` must record: failing node-id, isolation-run outcome, delta-inventory check, CEO consent. **Future D-77 candidate:** `orchestrate.sh` retries a full-suite failure in isolation N times before declaring DRIFT — a real drift reproduces, a flake does not — and skips the drift path if the failing test's file is not in `contracts.files`. |
| 2026-07-25 | Started the app with `uvicorn --host 0.0.0.0 --port 8000` after checking only that 8000 was currently free. Port 8000 is DeepSeek's (`DS4_URL`), and the app spawns `ds4-server` itself — so the next model load bound `127.0.0.1:8000`, which outranks a wildcard bind, and the model server silently inherited `localhost:8000`. A live chat died mid-session with every `/api/v1/*` call returning `{"error": "unknown endpoint"}`, and nothing in the symptom pointed at the port. | "Currently free" is not "unclaimed" — before binding a port, check the script-model endpoints configured in `src/services/models.py`, not just `lsof`. Bind `127.0.0.1`, never `0.0.0.0`: a wildcard bind lets a later specific-address bind win silently, where an identical bind would have failed loudly with `EADDRINUSE`. App port is 8080 — and it was ALREADY 8080 in `.claude/launch.json`; the README/CLAUDE.md quick start saying 8000 was stale and had never been the real convention. Read the project's own launch config before inventing a port; full port map documented under Commands. |
