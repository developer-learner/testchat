# 2026-08-02 — 0731 model add + v74 pipeline runs (handoff)

Session goal drifted twice; recording the whole arc. Tree wins on any
disagreement with this note.

## What the CEO asked for, in order

1. Add `deepseek-v4-flash-0731` (jmilnz 91 GB mixed-quant GGUF, antirez
   ds4-server runtime — NOT loadable by LM Studio/llama.cpp; it SIGABRTs) as
   a third script model.
2. Prototype-first: inline edit, verified live, then **reverted** — CEO chose
   the pipeline route with **0731 crewing both LLM seats** (EM + coder).
3. Conductor took the TPM role too (CEO delegation this session).

## Infra now standing

- `~/dev/ds4/run-server-0731.sh` — ds4-server, port **8005**, `--ctx 32768`
  (bumped from 16384 for EM prompts), kv-disk `~/.ds4/server-kv-0731`.
- Servers at handoff: ds4-0731 on 8005 UP; testchat uvicorn on 8080 UP
  (running PRE-refactor code from memory — do not restart it against the
  current mid-refactor tree and expect threads persistence to work);
  LM Studio API on 1234 UP (`lms server start` was run).
- Seat routing (D-53 per-invocation env, models.env untouched):
  `SWBP_EM_MODEL` / `SWBP_CODER_MODEL` against `SANDBOX_LLM_HOST=host.lima.internal
  SANDBOX_LLM_PORT=8005`. **ds4 model-id trick:** id `deepseek-chat` = same
  0731 weights in NON-thinking mode; id `deepseek-v4-flash-0731` (or any
  other alias) = thinking mode, high effort. This is ds4-server behavior,
  not a separate model.
- 0731 capability probes (before pipeline use): two hard prompts
  (dot-notation config lookup; ConfigStore deepcopy-both-directions) —
  correct, format-compliant, ~30–37 t/s, thinking ~1.3–5k tokens. Beat
  qwen3.6-27b-under-LM-Studio (which never emitted a final answer inside
  2000 tokens; partly an LM Studio reasoning-parse config issue).

## Why the tree is mid-refactor: v72/v73 were frozen but never built

Last `[success]` is **v71** (`d80664a`). v72 and v73 (M33 conflict-safe
revisioned persistence, 4 files, 20 delta tests) refroze + planned with no
task commits. CEO chose: ship v73 through the pipeline first, then the model
add. The model-add spec I authored is **parked, complete, renumber-on-entry**
(see "Parked M34 staging" below).

## v73/v74 pipeline attempts — full sequence

**Run A** (v73; both seats thinking `deepseek-v4-flash-0731`):
coder strike 1+2 = "reply contained no edit blocks" — thinking consumed the
output budget, content empty. Killed the run. Gotcha: **ds4-server is
single-flight and keeps generating after client disconnect** — a queued
probe waits forever; SIGINT the server process to abort.

**Run B** (v73; both seats non-thinking `deepseek-chat`): T1
(`src/services/storage.py`) — 4 coder attempts across 2 strike windows +
1 EM consult (diagnosis JSON was schema-valid; verdict `brief_wrong`;
revised brief was good) → caps exhausted → TPM escalation bundle. Left 3
`[task T1]` commits (2662d86, 0dfbc73, 2ea76aa) of close-but-wrong code on
main; non-UI suite at that point: 21 failed / 111 passed.

**TPM correction (me), frozen as v74** (`62ff1e3 [refreeze v74]`):
read the frozen oracles against the coder's file; three defects diagnosed:
1. `save_snapshot` passed constant `expected_revision=0` → every second
   compat save raised `SnapshotConflict` (the "revision conflict" evidence).
2. Legacy raw-list primary unreadable (`_read_raw` returned None for
   non-dict JSON) → AC-137/138 data-loss failures.
3. M24 quarantine-on-load dropped entirely; an out-of-scope `.bak`
   auto-restore was invented instead.
ERD-DELTA v74 names each defect normatively ("repair, don't rewrite");
tests restaged **byte-identical** (M31 empty-delta workaround);
DELTA-v74.json healthy (20 delta tests). D-75 warned 7 tests already pass —
expected carried-forward M8/M24 behavior, not vacuous.

**Run 1** (v74; EM non-thinking): EM reply had top-level key `"plan"`
instead of `"tasks"`, twice, despite validator feedback embedding the error
AND its own prior reply. Plan CONTENT was excellent both times. Halt.
Left `tasks/plan-subtree.json` untracked.

**Run 2**: pre-flight fail-closed on that leftover file (good gate).
Cleaned; budget refreshed (`rm .pipeline-state/plan_revisions*` — the halt
text itself names this remedy).

**Run 3** (EM thinking): correct shape
`{"erd_version":74,"version":2,"tasks":[...]}` — but `finish_reason=length`
at the default 8192 combined (thinking+content) cap → invalid JSON.
**Asymmetry learned:** unparseable EM reply dies immediately (no retry);
schema-valid-but-wrong-shape consumes a plan revision with feedback.

**Run 4** (EM thinking + `SWBP_MAX_OUTPUT=16384`): both attempts parsed,
right top-level key, but all 4 task objects failed "not a complete task
object" — `TASK_REQUIRED = {id, file, depends_on, brief, contracts, tests}`
(validate-plan.py:105) and the validator does NOT name the missing key.
Post-halt diff of attempt 2's raw: **every task named the field
`test_nodes` instead of `tests`** — missing `tests`, extra `test_nodes`,
nothing else wrong. Halted after 2 revisions. NOTE for any retry:
`MAX_BRIEF_CHARS = 2500` is the next tripwire — run-3's T1 brief was near
that ceiling.

**Confirmed pattern across runs 1/3/4:** 0731's plan content is
consistently right; it invents plausible key names wherever the prompt
leaves the schema implicit (`plan` for `tasks`, `test_nodes` for `tests`).
The subtree prompt says "map node-ids to your tasks" but never names the
`tests` field. Pure D-107-class prompt gap.

## Findings that belong upstream (blueprint), not fixed here

- **EM subtree prompt never enumerates the six required task keys** — same
  defect class D-107 already fixed for D-64/empty-contract rules by putting
  validator rules verbatim in the prompt. This is THE root cause of runs
  1/3/4: the model must guess the schema.
- Validator message "not a complete task object" should name the missing
  keys (Rule 3 allows detection-reporting improvements; still control-plane,
  left untouched this session).
- `llm-call.sh` `max_tokens` is combined thinking+content on ds4; any
  thinking seat needs `SWBP_MAX_OUTPUT` ≥ ~12k. Prompt ~15k tok + 16384 out
  fits the 32768 ctx with little margin.

## State at handoff

- main at `62ff1e3`, several commits ahead of origin, unpushed.
- Untracked: `tasks/plan-subtree.json` (run-4 artifact; REMOVE before any
  new orchestrate run or pre-flight fails on dirty tree).
- `.pipeline-state`: spec v74; T1–T4 pending; plan not yet validated.
- Suite: non-UI 21F/111P (mid-refactor, expected); UI/Playwright tests
  error on host (env) — sandbox is the arbiter.
- Run 4 attempt 2 possibly still running (`orch-v74.log` tail tells; the
  whole log of every run this session is that one file).

## Parked M34 staging (the actual model-add — renumber before use)

`project-trail/2026-08-02-m34-staging/` holds the COMPLETE refreeze staging
for the 0731 catalog add, authored against the v73 tree: PRD M34 section
(AC-149..154), ERD-DELTA, contracts.json (2-file scope:
`src/services/models.py`, `src/api/models.py`; quote-agnostic smoke
checks), and the updated `tests/test_models_service.py` (registry
set-equality + a new schema-Literal test). Before staging into
`scripts/.approved/incoming/`: bump erd_version to the then-current+1,
retitle the delta, and rebuild the PRD copy from the THEN-current frozen
PRD (it was built on the v73 PRD and is stale the moment another freeze
lands).

## Resume paths, in preference order

1. If run-4 attempt 2 validated: nothing to do — task DAG is running;
   watch `[task T*]` commits and the mapped-test verdicts.
2. It halted again (`test_nodes` vs `tests`). Smallest in-lane fix =
   refreeze adding one ERD-DELTA paragraph giving the LITERAL task-object
   skeleton — `{"id": "...", "file": "...", "depends_on": [], "brief":
   "...", "contracts": [], "tests": ["<node-id>", ...]}`, keys exactly, no
   others (`test_nodes`, `acceptance`, `erd_version`, `regression`, and
   `status` are all rejected) — which also auto-refreshes the plan budget.
   Then:
   `rm -f tasks/plan-subtree.json` and re-run:
   `limactl shell dev-vm sh -c 'SWBP_EM_MODEL=deepseek-v4-flash-0731 SWBP_CODER_MODEL=deepseek-chat SWBP_MAX_OUTPUT=16384 SANDBOX_LLM_HOST=host.lima.internal SANDBOX_LLM_PORT=8005 ./scripts/orchestrate.sh'`
3. Fallback (halves the experiment; CEO call): EM seat →
   `SWBP_EM_MODEL=ddalcu/Qwen3.6-27B-4bit-MTP-MLX-Serve` +
   `SANDBOX_LLM_PORT=11234` (mlx-serve) or the mtplx seat on 8001, keep
   coder on 0731 non-thinking via 8005. Mixed hosts need per-role
   host/port — check llm-call.sh profiles before assuming one env pair
   covers both seats.
4. v73 can still be CEO-directed as a hand-build (offer was made and
   authorized once, then superseded by "pipeline with 0731 seats").
   The three-defect diagnosis above is the complete repair list.
