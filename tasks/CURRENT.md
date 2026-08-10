# CURRENT.md — Session Notes

> Human-facing status page, NOT the spec. Frozen spec lives in
> scripts/.approved/ and changes only via scripts/refreeze.sh (D-31).

---

## State at 2026-08-09 — model-management bundle shipped as a CEO-directed direct fix; pipeline halt formally closed

- **CEO ruling (this session):** the Lima VM + EM/coder + sandbox are for milestone feature runs ONLY, not ad-hoc bug fixes. The model-management bundle went through the pipeline only because it was inherited as a spec-v100 milestone; that was the conductor's mistake. Bug fixes now go direct — no refreeze/orchestrate — unless the CEO explicitly asks for the milestone path.
- **HALT CLOSED:** the orchestrate halt (escalations/T2 — coder strikes, caps exhausted) is formally resolved as "spec became a direct fix". The `.pipeline-state/` run state and `.tpm/outbox/` staging were removed; the escalation record is archived in git history (`6aa4351` tree).
- **Shipped as ONE commit** `7bfc622` (pushed, `origin/main` force-updated from the milestone-churn `6aa4351` to the clean `15c1ee1` base + this commit — the refreeze v100/v101/v102, plan, T1/T2 commits are gone from the remote):
  - AC-163: unload terminates only a positively identified model server (identity token = last NON-NUMERIC token of the entry command, basename-matched against any cmdline token). The previous `command[-1]` rule false-positived on the fixture convention `[python, -c, <src>, <port>]` — a foreign `python -m http.server <port>` matched. Proven live: the AC-163 gate now refuses to kill the real `omlx-server` on host port 8000 (`DEEPSEEK_READY_URL`), which the v99 code would have killed during nemotron-load eviction.
  - AC-164: failed unload → 503 (not 200).
  - AC-165: load/unload endpoints are sync (threadpool) — event loop never blocks.
  - AC-166: failed settings save keeps the modal open + shows "Save failed — your changes were not applied." (`settings-status` in index.html/chrome.js).
  - Regression tests `tests/test_model_lifecycle.py` + `tests/test_ui_settings.py` ride the same commit (direct-fix mode — no refreeze).
- **Verification:** full frozen suite **205/205 green on the host** (5m05s) under `DS4_URL=http://127.0.0.1:1` isolation (dead port — matches the sandbox condition). WITHOUT the override, the two nemotron-load tests fail on this host: a live `omlx-server` on 8000 makes the eviction pass see deepseek-v4-flash "loaded", and the AC-163 gate correctly refuses to terminate the unidentified process → `could not evict` → 503. In the sandbox (no live servers) both are green. Not a defect; the sandbox and the isolated host agree.
- **Frozen-manifest note (future refreeze):** `test_model_lifecycle.py` / `test_ui_settings.py` are committed but NOT in the v99 `frozen-manifest` (INV-1 — the phase-gate rejected the commit; bypassed with `--no-verify` per CEO direction, M33 live-fix precedent, recorded in the commit message). The next real milestone freeze (`refreeze.sh`) will re-stage tests/ and adopt them; until then, any test-touching commit gets the same INV-1 rejection (expected).
- **Frozen spec stays v99** — `scripts/.approved/` reverted to the v99 state; the v102 spec lives only in git history. `tasks/plan.json` at base; tree clean; nothing unpushed.

---

## State at 2026-08-10 — CI fully green across the fleet; control plane back in sync with the restored blueprint

- **First green CI in repo history:** testchat `selftest` ✓, `test` ✓, `check-drift` ✓ (run 31350596301, push `8608abe`); blueprint `e9c2473` (`CI` ✓ + `check-drift` ✓). Local drift check: `in sync with template@e9c247359011` (rc=0).
- **Blueprint restoration:** the previous birth ref `d2e869ac` was force-pushed out of the blueprint's history (check-drift: "not our ref"). D-131 control-plane content it carried (tpm-lint.sh, validate-plan.py D-131 resolution, D-131 selftests) is restored as blueprint commit `e9c2473`, which also fixes the blueprint's own ruff-0.16 fixture bug. testchat had been ahead of its template; both repos now agree at `e9c2473`.
- **Three commits on top of the halt-closure notes** (testchat, pushed, `origin/main` = `8608abe`):
  - `f569528` — the two direct-fix regression tests are now PINNED in `scripts/.approved/frozen-manifest` (INV-1 bookkeeping). Test-touching commits no longer need `--no-verify`; a future refreeze will still re-stamp them.
  - `916347c` — S6 selftest fixtures reordered for ruff 0.16's default isort select (I001 was failing the D-67 staged-test lint); `.manifest-template` regenerated. 318/318 selftests green under ruff 0.15.15 (host) and 0.16.2 (CI venv).
  - `8608abe` — `.template-version` repinned to `e9c247359011…` + `.manifest-project` regenerated (control-plane-tamper gate requires the regen in the same commit).
- **Working-tree incident (no damage):** a half-popped stash ("stale plan.json from interrupted M35 run") had also carried halted-run versions of `src/services/models.py` + `tests/test_model_lifecycle.py` + `tests/test_models_api.py` and silently overwrote the committed `7bfc622` fix in the working tree. Caught via `git status` before anything was committed; restored from HEAD; contaminated stash dropped. `origin/main` was never affected.

---

## State at 2026-08-09 — data-safety milestone complete at spec v99; PM-review P1s closed in-delta; model-management bundle queued

- **`[success] spec v99` (`077acab`)** — full frozen suite ALL PASS (282s, 202 node-ids); the PM-review flaky quarantine-warning UI test (AC-80) is now deterministic. Branch 50 commits ahead of origin/main.
- **What v99 closed (both delta-scoped P1s from the 2026-08-09 PM review of v98):**
  - AC-161 quarantine-failure visibility: `load_versioned_snapshot` raises `SnapshotUnavailableError` when the quarantine rename fails (all four paths, `7690a45`); GET `/api/v1/threads` maps it to `503 {"detail": "snapshot unavailable"}` (`cdf76f8`) — broken storage is never reported as healthy-empty.
  - AC-162 single-owner hydration: app.js renders `history unreadable (backup kept)` from `data.quarantined` (`5194fb4`); the racing script-eval writer in threads.js is removed (`a71e3c1`).
  - New frozen test `tests/test_storage_service.py::test_quarantine_rename_failure_is_unavailable` (all four quarantine paths; went red pre-implementation). Its `test_mapping` pin is deferred to the next delta (check-spec-delta requires frozen node-ids; v88→v94 precedent).
- **Remaining PM-review findings (next milestone — model-management bundle, est. 60-90 min):** `src/api/models.py:84-93` async endpoints block on synchronous startup/shutdown polling; `src/api/models.py:79-81` unload returns 200 on failure; `src/services/models.py:220-226` port-based PID inference can kill an unrelated process; `src/static/chrome.js:124-129` settings dialog hides failed saves (P2). Out-of-delta: CSRF, source-URL validation, accessibility, doc drift.

---

## State at 2026-08-08 (session end — 2) — hygiene batch done, CEO memos never drafted, stop confirmed

- Both repos clean and IN SYNC: testchat HEAD `d0ac352` (backlog: AC-48 audit DONE), template HEAD `1f7d1c4` (drift clean).
- AC-48 audit closed and recorded (`tasks/BACKLOG.md`, commit `d0ac352`): text recovered verbatim from refreeze v20 (`51149c1`); §5.1 lint FAILS — "end the stream" is mechanism, no `such that` post-condition; frozen test does pin the partial-reply retention + Send restore pair, so observable coverage exists in test form; re-cut clauses drafted for the next TPM bundle (ride along AC-42's).
- testchat `.opencode/node_modules` removed (101M, gitignored, regenerable from package.json) — nothing committed, tree clean.
- **NOT DONE** — deliberately stopped mid-step before drafting either CEO memo (manifest-drift guard; statuses coverage). They were waiting on the CEO conversation anyway; nothing repo-visible needs them.
- loosed at the still open-info `~/.lima/dev-vm` still running (last session's). Stop when convenient: `limactl stop dev-vm`.

## State at 2026-08-08 (session end) — handoff: S6 + D-128 landed; the only open P1 is AC-42 (TPM lane); two CEO directional decisions pending

**Fresh-session entry point:** read `AGENTS.md` (CLAUDE.md) first — their correction log, operating rules, and lane ladder are the memory layer. Two repos, both clean and IN SYNC: blueprint HEAD `228d600`, testchat HEAD `db95e2e` (template ref `0598ab6`). **A parallel conductor session is live in the same workspace** — one-writer per file; it still has mypy-into-sandbox parked in its lane; don't pick that up without coordinating.

**What shipped in this session (both repos, 304 selftests, in sync):**
- **S6 reverse-direction lint (the backlog P1, done):** `scripts/check-test-direction.py`, wired as an S6 preflight in `refreeze.sh` (runs on merged preview). Check 1 rejects URL-verb mocks that ignore their URL arg (or bare `Mock()`) — **scoped to delta-touched tests only** (D-128 amend: the live frozen suite carries 9 legacy whole-world mocks in test_models_api/service; a whole-suite halt would brick every refreeze — caught by the parallel session's live probe; valuable lesson logged). Check 2 rejects a carried test citing an AC the delta ADDS. 4 selftests pin both directions; live-suite validation done (0 findings; staged mock still rejected).
- **DECISIONS.md: D-128** in both ledgers (blueprint full entry + testchat mirror; ledger travels with code rule).
- em.md verbatim-node-ids requirement (other session) — shipped.
- D-127 sandbox non-root proof, D-126 metrics durability — shipped earlier this arc.

**Remaining board (CEO-prioritized):**
- **P1: AC-42 flake hardening** — the only P1 left; it's a TPM/refreeze item (needs the TPM shuttle round-trip then `refreeze.sh` on green preflights). Prepare the staged bundle, run `tpm-pack.sh`, hand the bundle to the CEO verbatim (D-49), apply via `tpm-unpack.sh` + `refreeze.sh` on green.
- **P1: (MSTPLX demoted by CEO 2026-08-08)** — model-discovery milestone is OUT; don't schedule it.
- **P2 conductor lane (mine):** the two collated "it's mine" hygiene items — AC-48 audit, testchat `.opencode/node_modules` cleanup; plus manifest-drift doc guard + status.py coverage **awaiting CEO directional decisions** (they were surfaced as decision-memos, not asked to decide alone).
- **P2 (other agent's lane):** mypy-into-sandbox, and the changed-tests ordering item is a TPM refreeze item per its own lane check (conftest.py is INV-1-pinned).

**CEO positions recorded 2026-08-08:** no human approval at refreeze (D-121, auto-apply on green preflights); the CEO is directional, not technical, at that stage. MTPLX demoted. Conductor stack = the table I sent (cleanup have the answers).

**Next move for a fresh session:** (1) confirm both heads/in-sync, (2) take the conductor hygiene batch (AC-48 audit + node_modules cleanup + whichever CEO decides), (3) when green, prepare the AC-42 bundle via the TPM shuttle (D-49) — no diff needed in the code first; the board only needs the CEO's two decisions to complete the table.

---

## State at 2026-08-06 (late) — M35 v84 run root-caused: not the EM, not the ordering — D-64 swept pinned node-ids

Verified against the tree, the run log, and `.em-archive/2026-08-06_192053_plan-subtree/`.

**The v84 run failed at plan phase** (HEAD then: `6478277 [refreeze v84]` +
`ef13dc8 [plan]`, ORCH_EXIT=1): "PLAN GATE FAIL: task T1: no mapped tests and
no smoke_check in contracts for 'src/static/app.js'" in `--affected`, after
"plan ok (v3)" had committed ef13dc8.

**The other LLM's diagnosis was wrong on both counts:** it claimed the EM
mapped everything onto T2 and that the root cause was the acceptance check
running before the placement block (its fix: reorder + rerun). Evidence:
- The EM's reply was CORRECT — archived `reply.json` has T1 = the 5
  app.js-pinned node-ids, T2 = the 1 index.html-pinned node-id.
- The committed plan was NOT the reply: ef13dc8's tasks are byte-identical
  to the prior v82 plan (3+/3- diff = version fields only).
- The loss site: `validate-plan.py`'s D-64 browser block moved T1's PINNED
  browser tests to the final task (it never consulted `contracts.test_mapping`),
  the `AUTO_PLACED` write-back persisted the emptied plan, and the second
  validate (`--affected`) judged the persisted plan — empty T1 + no
  smoke_check (v84 retired the vacuous one) = gate fail. The reorder fix
  would not have helped — it would have failed plan-ok and burned the EM
  budget.

**Fix (landed in this commit):** D-64 now exempts test_mapping-pinned
node-ids — pinned behavioral ownership is the authority; D-64 is only the
fallback for unpinned browser node-ids. Selftest
`test_d64_leaves_mapping_pinned_nodeid_at_owner` pins the regression.
Verified end-to-end with the archived v84 inputs: merge → plan ok → plan
keeps T1:5/T2:1 → `--affected` over DELTA-v83/v84 exits 0. 288 selftests
green. Manifest regenned.

**Status:** v84 M35 run may be re-run exactly once now that the gate defect
is fixed. The other LLM's reorder theory should be discarded.

---

## State at 2026-08-06 — control-plane session: D-121 + v83 pin backfill + D-122 landed; M35 (v84) in-flight in the other LLM's lane

Verified against the tree, not from memory or a prior handoff.

**Frozen spec:** v83 (`scripts/.approved/VERSION` = 83). Installed at
`d7caf3b [refreeze v83]` — auto-approved under the new D-121 policy
(`auto-approved (D-121); DIFF-SHA 0e81d86a…`). This was the CEO-approved
40-pin contracts backfill: every contract entry now names its owning
`src/*.py` file (15 routes → handler files, 21 schemas → defining files,
4 errors → raising files), the precondition for the EM contracts-trim
(D-120) to slice context without losing entry bodies. `erd_version 83`,
`changed_files: []` — a pure pin freeze. Ownership map derived from the
tree: `chat.py` / `threads.py` (split ownership noted for 422 + HistoryEntry),
`models.py` (both 503s), `main.py` (static mounts), `settings.py`,
`status.py`.

**Working tree:** NOT clean — the M35 v84 freeze is in progress in the
other LLM's lane right now (uncommitted: `ERD-DELTA.md`, `contracts.json`,
`tests/test_ui.py`, new `DELTA-v84.json`). Do not touch any of those.
Everything else is committed.

**HEAD:** `38a9425 control (D-122)` — the delta-completeness gate.

**What landed this session (commits, in order):**
- `1cce8e4 control (D-121)` — refreeze has no human approval step: the
  `--approve <sha>` / `--interactive` paths die on use; auto-apply on green
  preflights is the only mode; `--diff` stays a read-only preview. CEO
  ruling verbatim in DECISIONS.md D-121. 283 selftests green at the time.
- `d7caf3b [refreeze v83]` — the 40/40 pin backfill (above). DELTA-v83.json
  records 40 changed_contract_ids, 0 tests, 0 files.
- `38a9425 control (D-122)` — the delta-completeness gate (CEO-authorized
  after a brief): `check-spec-delta.py` now fail-closes two shapes the
  DELTA-vN bookkeeping cannot see — (1) ERD-DELTA marks a frozen test
  `(UPDATED)` while the freeze stages no bytes for its file (the v82
  incident: DELTA-v82 recorded `changed_tests: []` for a claimed test
  update), and (2) contracts change only bookkeeping-invisible keys
  (`test_mapping`/`smoke_checks`/`files`/`no_edit_files`) with no declared
  changed_files, staged test bytes, or entry deltas. Marker matching is
  case-sensitive so historical prose never trips it. Verified live: passes
  on the v84 staging, and fires on a simulated v82 shape against real repo
  data (both messages). 287 selftests green (4 new). DECISIONS.md D-122.
- `8178507` (earlier this session) — retired DELTA-v1..v78; deltas v79–v83
  remain on disk.

**M35 (v84) staging, validated but handed off:** the v84 staging was
assembled (v83-approved pins inherited + M35's `test_mapping` 6 node-ids
→ `app.js`/`index.html` + `changed_files` + `smoke_checks` retired) and
passed `check-spec-delta.py` + a dry-run `--diff` (DIFF-SHA `a7448f36…`)
before handoff. The install + orchestrate run belongs to the other LLM —
refreeze is unattended under D-121, no approval step needed.

**Open thread (carried):** the pipeline declutter/proportionality work
from the M34 entry — still untouched.

---

## State at 2026-08-04 — M34 shipped (spec v79); tree clean

Verified against the tree, not from memory or a prior handoff.

**Frozen spec:** v79 (`scripts/.approved/VERSION` = 79). Shipped at
`79a2d20 [success] spec v79`. Full frozen TPM suite green against v79.

**Working tree:** clean — nothing uncommitted, nothing unpushed to inherit.
`.pipeline-state/tasks/` and `.pipeline-state/escalations/` are empty, the
expected post-success state (D-99), not lost state.

**HEAD:** `d354601 [bugfix] orchestrate: exit trap no longer flips a green run
to exit 1` — a one-commit follow-up so a green run stops falsely exiting 1.

**What M34 was.** A small 2-task delta adding the `deepseek-v4-flash-0731`
model to the catalog, both tasks landed attempt 1:

- T1 (`src/services/models.py`) — added the `deepseek-v4-flash-0731`
  script-model registry entry.
- T2 (`src/api/models.py`) — widened the `source` Literal unions
  (`ModelInfo`, `CatalogEntry`, schema) to accept `"deepseek-v4-flash-0731"`.

Commit trail: `b5a2769 [plan]` → `a3eefed [task T1]` → `d1714b5 [task T2]` →
`79a2d20 [success] spec v79` → `d354601 [bugfix]`.

**Open thread (not started).** The pipeline declutter/proportionality work —
make the machinery proportional to the change, cut ceremony that never caught
a real failure. Starting point:
`project-trail/2026-08-04-pipeline-declutter-proportionality.md`; its plan
item 1 (the evidence audit that gates any cut) is untouched.

> The M33 T1 finding below is superseded — M33 closed out (v77, see the
> Results block for the 2026-08-03 manual close-out) and M34 has since shipped.
> Kept as history.

---

## Finding at 2026-08-02 — M33 T1 brief is bloated (3 of 4 defects stale)

Non-mutating diagnostic run outside testchat's tracked lanes:

- Frozen test-report from M33 attempt 1 (`.pipeline-state/escalations/T1/test-report.json`) shows **12 of 13 tests pass** against `src/services/storage.py` at HEAD (`42d54be [task T1] attempt 1` — the state the coder reached before retries exhausted). The only failure is `tests/test_storage_service.py::test_corrupt_snapshot_is_quarantined` — exactly defect (3) in the brief.
- Defects (1), (2), and (4) are satisfied by the current source (save_snapshot reads current revision under the lock; legacy list load returns `data, 0`; there is no `.bak` fallback on load — only on save).
- Additional evidence: coder seat swapped to `deepseek-v4-flash-0731-antirez` via ds4-server on :8005, output budget raised from 4K → 24K. Model produced a complete, well-anchored SEARCH/REPLACE block that the applier accepted (file compiles + lints). But the block fixes the wrong branch — it added quarantine on invalid-envelope, not on JSON-parse-fail. Even with the working seat, the misspecified brief steers the coder off target.

**Implication:** T1 needs re-scope, not more coder attempts. Split into single-defect brief for defect 3 only.

**Untouched:** T1 status still `escalated`, `bundle.md`/`test-report.json`/`BATCH.md` intact, real `storage.py` unchanged, testchat unpushed.

---

## State at 2026-07-30 — M32 shipped; control plane consolidated

**Frozen spec:** v71. M32 completed at `[success]` commit `d80664a`.
The current macOS-host verification is **178/178 passed**; control-plane
verification after the canonical template sync is **193/193 passed**, with
manifest integrity, plan validation, lint, and type checking also green.

**M32 user-visible outcome.**

- The model selector no longer becomes locked after a thread has messages.
- A user can switch models in the middle of a conversation; the next send is
  routed to the newly selected model.
- Model choice remains sticky per thread and is restored on thread switch.
- The persisted `thread.locked` field remains for backward compatibility but
  no longer disables the selector.

**Pipeline/template state.**

- D-107 is canonical in `sw-dev-blueprint` at `704c129`: every behavioral
  freeze must carry a traceable `ERD-DELTA.md`, and the EM receives the
  validator rules it is judged against.
- Testchat synced that canonical control plane in `7b92123`; project-owned
  container, CI, and onboarding adaptations landed in `2df7abd`.
- An empty `.pipeline-state/tasks/` is expected after this successful run:
  the newest task commit is covered by the later `[success]` commit. D-99 now
  distinguishes that state from genuine mid-milestone loss, so no synthetic
  task markers or manual source rebuild are required before the next milestone.

**Release checkpoint (observed 2026-07-30).** `main` is published through
`bf521fe`; both GitHub CI workflows are green. The app is running at
`http://127.0.0.1:8080`, pointed at MTPLX on `127.0.0.1:8001`. MTPLX was
restarted through its supported CLI with strict warm-up: a direct completion
returned `MTPLX_OK`, and an end-to-end request through `/api/v1/chat` returned
`APP_OK`. Lima/Podman cleanup reclaimed 7.25 GB of unused images (VM use fell
from about 12 GB to 4.4 GB) without touching the 30 GB MTPLX model cache.

**Deployment limitation found.** The browser model catalog probes LM Studio's
non-standard `/api/v1/models` route, while MTPLX exposes the standard
OpenAI-compatible `/v1/models` route. Therefore MTPLX works through the chat
proxy but is not selectable in the UI; with both script-run models unloaded,
the Send control remains disabled. This is a product-contract gap, not a
runtime-health failure, and is queued in `tasks/BACKLOG.md` for a frozen-spec
pipeline milestone rather than hand-patched outside INV-1.

---

## State at 2026-07-27 session end (app.js split shipped + v66 ratify)

**Frozen spec:** v66. Suite **176/176** on the macOS host — the
2026-07-27 pytest run showed 173 pass + 3 Playwright thread tests flaky
under full-suite memory pressure; the same 3 pass 3/3 in isolation in
~19s. Same class as the AC-42 flake pattern in the correction log; not
a regression from the ratify (which touched no `src/` or `tests/`).
main pushed, nothing unpushed.

**What shipped since M29 / v65.**

- **`2579f07` — app.js split** (hand-build, not through the pipeline).
  959-line `app.js` split three ways: chat surface stays in
  `src/static/app.js` (550 lines: bubbles, SSE stream, stop, pollStatus,
  Send-with-unloaded-model, hover/copy/thinkToggle/newThreadBtn), themes
  and focus mode and settings and generic modal chrome move to a new
  `src/static/chrome.js` (171 lines, `window.Chrome = {}`), model
  dropdown lifecycle moves to a new `src/static/catalog.js` (304 lines,
  `window.Catalog = { fetchModels, refreshModels }`). AC-28 mid-chat
  lock moved verbatim; AC-104 cancel-reverts (focus/mousedown pre-change
  capture) preserved; overlay dismissal helpers shared across all
  modals; matrix-rain and phosphor titlebar side effects ride with
  `applyTheme`. Cross-module contract: `window.App = { appendBubble,
  pollStatus }` published from app.js for chrome and catalog to call
  lazily. Full plan-and-outcome record in
  `project-trail/2026-07-27-appjs-split-handoff.md`.
- **`361fbe4` — [refreeze v66]** — ratify freeze recording the split
  in the frozen spec: `chrome.js` + `catalog.js` added to
  `contracts.files` (16 → 18) and to the ERD `As-built architecture`;
  `app.js` smoke_check re-authored to post-split landmarks (`webToggle`
  / `pendingSources` / `【` / `pollStatus` / `queueRender` — the prior
  version's `ejectModelBtn` and `models/catalog` greps moved to
  catalog); new smoke_checks for `chrome.js` and `catalog.js`
  (quote-agnostic per D-88); `changed_files` set to the four files
  this hand-build touched. Zero test changes, zero AC changes; D-75's
  red-check correctly returned "no runnable test changes — nothing to
  check." Backlog `M13 — app.js module split (spec backfill)` closed
  in the following commit `7faec81`.

**Sequencing note.** The trail (handoff §Sequencing and the shipped
addendum) records the CEO decision that **item #1 — one small feature
through the pipeline as the live proof of D-86..D-94** rides
next, before any further ratify-shaped work. Candidates: draft
persistence, or AC-101 (a pinned-but-unloaded model on a locked
thread must be loadable in ≤2 interactions, blocking a real recovery
path today).

**Standing items carried forward (unchanged by this session):**

- `tasks/plan.json` is still at `erd_version 58` while VERSION is
  now 66 (the M29 warning below stands, updated). A next
  `orchestrate.sh` run re-derives the plan for v66. Both mitigations
  that make the re-derivation safe already landed at M29
  (`6557283` fail-closed on empty state, `2144d12` inverted
  `no_edit_files` derivation), so untouched files are protected and
  a stale plan is untidy rather than dangerous.
- `.pipeline-state/tasks/` still carries the 27 per-task `done`
  markers from the M29 v58/59 era. A v66 re-plan changes every task
  fingerprint and resets these to `pending`, then the derived
  `no_edit_files` protects the files no delta touches.
- The `.claude-md-pending.patch` "also open" note from the M29 block
  below no longer applies — the file is not in the tree.

---

## State at 2026-07-26 session end (M29 — "unloaded" means unloaded)

**Frozen spec:** v59. Suite **153/153** on the macOS host, in the sandbox
container, and in CI (`677034a`). main pushed, nothing unpushed.

**What shipped.** M29 fixed the P0 filed 2026-07-25: `unload_script_model`
returned `{"status":"unloaded"}` having killed nothing whenever the in-memory
`Popen` handle was gone (any `--reload` worker restart). Unload now discovers
the server by the **listening port** parsed from its `ready_url`
(`_find_listening_pid` → per-process `psutil.process_iter()`), terminates that
one PID, re-probes, and returns `{'status':'error'}` if the model is still
reachable. Load aborts rather than spawning when the other model cannot be
evicted, closing the two-models-resident RAM path. Discovery by process *name*
was rejected by CEO directive — `pgrep -f <basename>` also matches unrelated
processes that merely mention the script path, then SIGKILLs them.

v59 was a one-hunk refreeze: the carried-forward
`test_load_nemotron_expands_script_path` mocked `httpx.get` to 200 for *every*
URL, which made the other script model read as loaded and made new AC-104
correctly refuse to spawn — unsatisfiable alongside the AC. The mock is now
scoped to nemotron's own `ready_url`.

**READ THIS BEFORE THE NEXT `scripts/orchestrate.sh` RUN.**
`tasks/plan.json` is at `erd_version 58` while VERSION is 59, so the EM must
re-derive the plan. Fingerprints hash the whole task dict, so a re-derived plan
changes **all 12** and resets every task to `pending` — and
`contracts.no_edit_files` protects only 3 files. The coder would then be handed
`app.js`, `chat.py`, `threads.py`, `index.html`, `websearch.py` and the rest,
none of which any current delta touches. `T11.fp`/`T12.fp` are also empty while
their status is `done`.
**Both P0 mitigations have since landed** (`6557283`, `2144d12`): orchestrate
now halts pre-flight when task-state is lost, and a file the delta does not
touch never reaches the coder — 8 of 12 blocked on the M29 plan, against 3
before. The stale plan above is therefore no longer dangerous, only untidy: a
re-derived plan still resets every task, but the untouched files are protected.
**Residual to know about:** `--affected` includes transitive dependents, so
`src/api/chat.py` and `src/static/app.js` stay editable for a models-only delta,
and `app.js` maps 0 tests (smoke_check only). Watch those two if a run does go
through, or reconstruct the `done` markers against the re-derived plan first.

**Also open:** `.claude-md-pending.patch` (untracked) re-applies the port-doc
change CEO-reverted at `c4710cc` and adds a correction-log row — needs explicit
direction, and `CLAUDE.md` is pinned in `scripts/.manifest-project`, so applying
it means regenerating that manifest. T12 never executed (its 18 API tests pass
regardless). No formal `[success]` commit for M29, deliberately — producing one
requires the full re-plan described above.

---

## State at 2026-07-19 session end (post-M28 CEO live-fix sessions)

**Frozen spec:** v54 unchanged — no pipeline runs today; all work was
CEO-session live-fixes on top of the M28 manual close-out. main pushed
through `150dc22` (+ this note).

**Dropdown hardening — 11 post-`[success]` live-fixes total:**
- Morning batch (`6857d70`..`9da00ff`): load-cancel actually reverts the
  dropdown; status bar reflects actual loaded state; Send disabled
  without a loaded model / Eject greyed without a selection; redundant
  ✓ prefix dropped (native select already marks selection on macOS).
- Full-app bug-scan batch `b4c108b` (6 fixes, app.js): duplicate change
  listener corrupted thread.model on load-cancel (deleted); reload now
  restores a thread's saved model regardless of the hydrate/models
  fetch race; failed load can no longer leave a stale 🟢 glyph;
  pollStatus fires on modal open/cancel (status lagged up to 5s);
  unload id via dataset.modelId + encodeURIComponent instead of
  display-text parsing; error-path user push gains ts. Suite 150/150
  green at commit time; cancel + reload-restore paths browser-verified.
- Markdown code-span fix `e96a4e7`: renderInline placeholder-extracts
  code spans before the bold/em/link passes, so backtick content with
  ** or * renders literally. 7-case node harness + in-browser
  renderThink path verified.

**M28 postmortem filed:** `project-trail/2026-07-19-m28-impossible-spec.md`
(`14e2260`, placement rationale corrected `7cb3ceb`). Finding: all four
M28 recuts (v51→v54) were spec-layer TPM defects; the two local-EM
"failures" were an unimplementable v51 spec (catalog route frozen
without its files in contracts.files — validate-plan bijection), so
both EM model swaps chased the wrong variable. Placement rule (CEO):
incident docs stay in the project repo; blueprint gets only generic
process changes (parked in tasks/HANDOFF-blueprint-items.md), CEO
handles blueprint separately.

**AC-42 escalated:** on BACKLOG.md as P1 (`14e2260` — promised at
close-out, never added). New evidence (`150dc22`): reproduces IN
ISOLATION under memory load (nemotron + an LM Studio model resident) —
4/4 consecutive failures including at a clean commit, from the A/B run
that exonerated the markdown fix. Failure detail: by first expect()
attach the full reply had already streamed; the ~1.2s hold window was
missed. "Passes in isolation" only holds on an unloaded machine.
Suite verdict for `e96a4e7`: 149/150 with only that known node red,
manual-bypass guard from the correction log applied (isolation A/B +
delta check).

**Hand-fix ledger, honest:** M28 is the first materially non-zero
hand-fix milestone since M7 — 11 post-success live-fixes, all UI
interaction detail the frozen ACs never pinned. The UI-quality gap and
per-milestone hand-fix tracking are called out in the postmortem.

## State at 2026-07-17 session end

**Frozen spec:** v47 (M25 "Web-Informed Answers", `[success]` `5bb036c`,
133/133). v46 froze the feature; v47 was a same-day ERD-only recut after
the plan gate caught an overweight T7 brief (TPM defect, D-60 class).
Feature: per-message globe toggle -> one Tavily search -> at most 4
numbered sources injected (2000-char cap each) -> reply cites; sources
persist and re-render; search failure falls back to offline reply with
"web search unavailable"; toggle disabled when TAVILY_API_KEY unset.
External capture frozen (captures/tavily-search.json, live-probed
2026-07-17). AWAITING CEO DEMO (D-44).

**MLX seat trial (CEO-directed):** `ddalcu/Qwen3.6-27B-4bit-MTP-MLX-Serve`
via mlx-serve on host:11234 held BOTH seats for the whole run. Verdict so
far: coder excellent (7 files, all first-application-correct, incl. an
85-line new file whole; only gate-hygiene retries); EM good (first-try
valid plan; first-ever schema-valid production diagnosis — D-71 live-fired
and worked — though the diagnosis prose rambles); speed: coder 9-23s/task,
EM plan ~190-210s/emission, comparable to MTPLX band. MTPLX mapping backed
up at ~/.config/sw-dev-blueprint/models.env.mtplx-backup (VM).

**Session incident ledger (all resolved, template debts queued):**
1. v46 plan halt — TPM ERD overweight (fixed by v47 recut).
2. D-68 gate first-scan of app.js flagged 4 legacy empty catches the coder
   could not touch — cleared by CEO-approved live-fix `1eb4054` (comments
   only). Template debt: D-68 whole-file scan means any legacy file's
   first post-gate edit needs a justification sweep.
3. Consult lane gate mis-blamed the EM: T7's failed attempt was left
   uncommitted when consult ran. Template debt: strike cleanup must reset
   the tree before consult.
4. frozen-manifest had hashed 47 tests/__pycache__ .pyc files at freeze
   time -> false "spec tampered". CEO-approved strip `c72bb05`. Template
   debt: refreeze.sh must exclude __pycache__.
5. Two one-off full-suite flakes (markdown-readability, then a
   fixture-settle timeout) — each unreproducible in isolation AND in a
   manual full sandbox run; existing 2026-07-15 flake class. Watch: if a
   third timing flake lands, bump the 8GB dev-VM allocation before
   touching the spec.

## State at 2026-07-15 session end (handoff)

**Frozen spec:** v45 (M24 "History Never Dies", frozen 2026-07-15,
`9050b24`; 117 frozen tests — oracle proof: 7 new fail-on-current,
117/117 pass-on-intended). Prior: v44 `[success]` tagged, CEO-accepted,
pushed to GitHub (origin = developer-learner/testchat), feature-complete
by CEO decision — M24 is the one PM-audit data-safety hole (silent
corrupt-history destruction) plus the AC-83 hover-timestamp ratify.

**Shipped this sprint (M14–M23, v28–v44):** rain-on-matrix ratify, phosphor
terminal window, newest-thread-first sidebar, loadable-RAM counter
(status strip; predicts whether a model load will fit), thread search +
in-thread highlighting + hit counter with prev/next navigation +
visible-only hit counting (collapsed think-text excluded), M23 honest saves
(persist-failure indicator, threads role Literal 422, lint cleanup, flake
hardening). Escalation ladder armed (D-70) and validated — every rung fired.

**Models:** `qwen/qwen3.6-27b` holds BOTH EM and coder seats — mapping
verified in the VM copy of models.env (the copy the pipeline reads; the
host copy is reference-only). 35B retired. An `unsloth/qwen3.6-27b-mlx`
variant was benched head-to-head: no quality difference, slightly slower,
+5 GB — recommend unloading/deleting it. EM-seat production validation:
1 clean run (M21 plan); call it settled after ~3.

**M14–M22 CEO-ACCEPTED (2026-07-14):** all nine demoed live in the browser
and formally accepted, no exceptions. Verification evidence: rain renders in
matrix only and terminal titlebar in phosphor only (all 10 themes cycled);
new chat lands at top of sidebar; RAM counter live in status strip; "pebble"
search filtered 26 threads to the 2 containing it; hit counter/nav honest
(thread had 11 raw matches, 6 in collapsed think-sections, counter said 5 —
AC-74 measured in the DOM); current-hit loud vs other-hits subtle confirmed
in one frame. Themes additionally eyeballed by the CEO directly.

**CI GREEN (2026-07-14/15) — first fully green CI in project history.**
Chronicle: the audit round found bare `mypy src/` dying on duplicate module
basenames before checking anything (CI had been dark for the repo's whole
unpushed life). Fix chain: `--explicit-package-bases` → test step had never
run either (no PYTHONPATH, no chromium, no .cache dir) → models.py:37
arg-type live-fix (the one true mypy finding; CEO-authorized `0bbcfce`) →
coverage bar 80→75 (CEO-approved: Linux measures 78, macOS 83 —
status.py's RAM paths are mac-only; ratchet up at M23). Latest main
(template-update 883bf99, D-69) passed a fresh CI run first-try.

**Flake record for the next TPM cycle:** one slow CI run (32s suite vs
usual 19s) flaked two UI tests, both green on rerun and on the next fresh
run: `test_thinking_placeholder_shows_then_clears` (inherent observation
race — the test must attach within the stub's ~1.2s hold window) and
`test_sidebar_lists_newest_thread_first` (one-off count mismatch, likely a
late persist PUT from the prior test). Zero-retry law governs the sandbox
oracle; CI is a second, noisier environment. Harden both at the M23
refreeze.

**Open items:**
- Coverage ratchet: CI measures the 111-test suite; ratchet bar back up
  from 75 once Linux/macOS gap narrows
- EM diagnosis hardening: schema-retry or dense-diagnosis brief as template
  candidate (M23 exposed mid-tier diagnosis as the weak rung)
- Blueprint packaging: cheap-tier publish idea (honest README, repo
  public as-is) discussed, no decision
- LM Studio housekeeping: delete `unsloth/qwen3.6-27b-mlx` (+5 GB, benched
  strictly worse)

**Conduct notes for the next conductor:** verify state from the tree, not
from memory or summaries (this session's worst errors were stale-claim
errors); give the CEO a time estimate before every pipeline run and report
the first halt immediately; view user-visible milestones in a real browser
before presenting; the CEO gets plain-language claims, never diffs.

## Results

Full frozen TPM suite green against spec v44. Feature built and validated.

**M23 HONEST SAVES COMPLETE: `[success] spec v44` (`d9c17cb`), 111 frozen
tests, final subtree run 72s.** First milestone with: MTPLX serving both
seats (host.lima.internal:8000, drift-immune), MAX_TASK_STRIKES=2, and a
frontier conductor doubling as TPM (D-39). Browser-eyes verified live:
"not saved" appears when the backend dies mid-session, clears on recovery;
invalid-role PUT returns 422.

**Escalation-ladder validation (the run's second purpose) — VERDICT: every
rung fired, one EM weakness found.** Retry-with-evidence fired (T7 strike
1→2); EM consult fired; the diagnosis came back schema-invalid
(empty task_id) and the gate refused it — halting correctly. Data point
for D-66: the MTPLX 27b plans cleanly (3rd plan valid) but stumbled on
diagnosis, matching the historical mid-tier pattern. Ladder is no longer
dead code.

**Cost ledger, honest: 4 freezes (v41→v44), ALL THREE spec bugs the
TPM's (this conductor's):** (1) no_edit_files declared without smoke
checks — unsatisfiable EM puzzle, M8 class; (2) D-64 dependency edges
asserted in prose but never instructed — the EM transcribes, it doesn't
invent; (3) the new UI test miscounted replies (two sends in ONE thread
need count=2 in _await_reply — every prior two-send test used fresh
threads). The coder was blameless: T7 attempt 1 was character-identical
to the ERD prescription and burned two strikes on the TPM's test bug.
TPM lesson encoded: state DAG edges explicitly; walk helper defaults
before freezing a test; a no-edit declaration still needs an acceptance
signal. Gates D-65 (4 no-op tasks skipped coder), D-67 (lint gate green
at every freeze), D-68 (clean output passed) all did production duty.

Residue: three empty "New Chat" threads created during browser
verification/demo — CEO deletes by hand at leisure (scripted delete
clicks no-op; real gestures work).

**M23 CEO-ACCEPTED (2026-07-15).** Demoed live to the CEO: backend killed
under an open page → "not saved" in the status strip; backend restored +
save retried → warning cleared, RAM counter back. Claim accepted: "if a
save ever fails the app says so immediately, clears on recovery; frozen
test #111 re-verifies forever." No exceptions.

## Results

Full frozen TPM suite green against spec v45. Feature built and validated.

**M24 HISTORY NEVER DIES COMPLETE: `[success] spec v45` (`c343b27`), 117
frozen tests, full run 208s, zero strikes — every edit task passed on
attempt 1 (T1 storage.py, T2 threads.py, T3 index.html, T4 threads.js;
T5–T8 no-edit acceptance only, D-65).** Second consecutive
zero-hand-fix milestone. Pre-freeze oracle proof re-derived after the
authoring session aborted: 7 new tests fail-on-current, 117/117
pass-on-intended; a fourth amended exact-shape assert
(test_put_invalid_role_rejected) was found during the proof and the
PRD/ERD accounting corrected before freeze.

Browser-eyes verified live (scratch TESTCHAT_DATA, real history never
touched): healthy load shows empty history-status; corrupt snapshot →
app starts empty, "history unreadable (backup kept)" in the status
strip, `threads.json.corrupt-<ts>` preserves the unreadable bytes
exactly; saves continue while quarantine sits untouched; `.bak` holds
exactly the previous snapshot after each save; renaming the quarantined
file back restores the history and clears the flag; past-day bubbles
hover "Jul 12 23:19" (date ahead of time, AC-83 ratifying live-fix
`5a950ae`).

**M24 CEO-ACCEPTED (2026-07-15).** Claim accepted: a corrupted history
file can no longer destroy itself — it is quarantined bytes-intact and
announced in the status strip; every save keeps the previous snapshot
as .bak; recovery is renaming the quarantined file back. Frozen tests
re-verify forever. Pushed to GitHub same session.

## Results

Full frozen TPM suite green against spec v47. Feature built and validated.

## Results

Full frozen TPM suite green against spec v49. Feature built and validated.

## Results

Full frozen TPM suite green against spec v50. Feature built and validated.

## Results (M28 spec v54, manual close-out)

Full frozen TPM suite green against spec v54 except for one known intermittent
flake (`tests/test_ui.py::test_thinking_placeholder_shows_then_clears`, AC-42,
M9 timing-sensitive test). The flake is unrelated to any M28 delta
(catalog UI / eject button / confirm modals in T5/T7/T11/T12):

- Isolated: passes clean (1/1)
- Full suite: intermittent — passed 150/150 in an earlier full run this
  session; failed subsequent full runs at the same node-id
- Test scope: M9 SLOWPING placeholder behavior, no T7/T11/T12 code path touched

Manual `[success]` per CEO direction — bypasses the DRIFT halt because the
failing node-id does not observably exercise this delta's inventory. The flake
belongs on the backlog as a stability defect against M9, not as an M28 blocker.

M28 features live:
- T5 (index.html): modal markup, eject button
- T7 (app.js): fetch models + catalog, glyph prefixes, load-confirm/unload-confirm modals, eject always visible
- T11 (services/models.py): list_model_catalog() with per-model loaded state
- T12 (api/models.py): GET /api/v1/models/catalog

Feature built and validated (aside from noted flake).

## Results

Full frozen TPM suite green against spec v56. Feature built and validated.

---

## Session 2026-07-25 — bug-claim review (conductor seat, no build run)

Three filed claims independently verified against `c4710cc` (confirmed
byte-identical to `1204546`). **All three confirmed**; two were understated by
the original report and one carried two factual overreaches. Full evidence,
reproduction steps and the spec lint:
`project-trail/2026-07-25-unload-spec-lint.md`.

- **Defect 1 (P0)** — unload reports success without verifying the process died;
  RAM mutual exclusion silently fails. `--reload` orphaning verified directly.
- **Defect 2 (P1)** — locked thread pinned to an unloaded model is a dead end
  (26/47 threads affected). Live-reproduced in a browser.
- **Defect 3 (docs)** — **fixed this session** in `README.md` + `CLAUDE.md`:
  documented run command bound port 8000, which is ds4-server's. Now 8080,
  matching `.claude/launch.json`. Note this restores the substance of `f3cb479`,
  reverted in `c4710cc` as part of a churn cleanup — the CEO's own revert
  rationale names 8080 as the correct value.

**Root cause (both code defects):** the frozen ACs specify mechanisms, not
outcomes. AC-95 mandates "SIGINT the process and return `{status:unloaded}`",
never "the model is no longer running", so the frozen test asserts
`send_signal` on a `MagicMock` and cannot fail. Lint over 77 reconstructed ACs:
process lifecycle fails 5 of 8, file lifecycle passes 9 of 9.

**No `src/` or `tests/` changes** — outside the conductor lane (D-40) and INV-1.
Both code defects need a TPM spec delta; draft replacement ACs are in
postmortem §6 and filed in `tasks/BACKLOG.md` as the top three Up Next items.

**Next step (CEO):** run `scripts/tpm-pack.sh`, take the bundle to the TPM web
chat with postmortem §6 as the delta request, land via `scripts/refreeze.sh`.

**State hygiene:** no production state mutated — `data/threads.json` verified
byte-identical (`bcab36da...`) before and after; all spawned test processes
cleaned up; app left stopped, as found.

## Results

Full frozen TPM suite green against spec v71. Feature built and validated.

## Results (M33 spec v77 — manual close-out 2026-08-03)

  Full frozen TPM suite green against spec v77: 192/192 host AND 192/192
  sandbox at HEAD. Feature built and validated. Close-out performed manually
  after an orchestrate re-execution incident (over-wide DELTA-v77 + stale
  v74-era T4 brief re-ran completed tasks); app.js reverted to the
  proven-green implementation, T4 escalation resolved as spec-defect with no
  code owed. Completion ledger recorded via completion-ledger.py (4 tasks,
  app.js sha 20b75f27). Full incident record: project-trail/2026-08-03-m33-closeout.md.

## Results

  Full frozen TPM suite green against spec v78. Feature built and validated.

## Results

  Full frozen TPM suite green against spec v79. Feature built and validated.

## Results

  Delta-mapped frozen tests green against spec v84 — feature done (verdict scope: mapped tests only, D-112). Feature built and validated.

## Results (EM prompt context trim, control-plane)

  Both remaining full-file context loads are gone from the EM plan prompts:
  - **Contract ids now scoped** (`contract_ids()`): ids owned by a
    delta-named file, module-matching entry_points, or the ERD-DELTA / a
    frontend UI file ship; unattributed `ui:*`/`external:*` route ids and
    entries with no owner file are dropped. Empty array is always legal and
    contract-repair + the validator still catch bad ids.
  - **Full-emission node-ids now scoped** (`NODEIDS_SCOPE`): the greenfield
    plan call ships the union of the active deltas' `changed_tests`
    (`.pipeline-state/nodeids-scope.txt`, D-119-aligned), falling back to
    the full `test-nodeids` file only when no active delta range exists.
    This was the last site still shipping the accumulated 198-id suite.
  - Selftests: 289/289 green — `test_plan_full_emit_scopes_nodeids_to_active_delta`
    (drive-level, exercises the D-113 mirror extracted into drive-plan.sh),
    updated D-119 guard (full file ships at no site unconditionally),
    existing contract-id/rule guards intact. `.manifest-template` regenerated.
  - No spec change, no state mutation — control-plane only.

## Results (audit follow-up — TPM consolidation v85 + ui pinning v86, control-plane + spec)

  Milestone-audit follow-up (the CEO's ask about the "remaining full-scope"
  items in the EM/coder context):
  - **v85 consolidation** (`e9ce192`): staged PRD.md + ERD.md folding the
    composer milestone (M35) out of ERD-DELTA, retired ERD-DELTA, created
    the empty DELTA-v85 marker. Chore `70f863c` removed the dead
    DELTA-v79..v84 stack — the delta ladder collapsed to the standing spec.
  - **v86 (`4383616`)**: the last audit item — every `contracts.ui` testid
    now pins its behavioral-owner file (`data-testid` → the script whose
    logic drives it), closing the D-120 gap on the UI contract block. The
    milestone slice (`contracts-delta.py`) gained `ui` in its pinned keys:
    out-of-inventory testids index to a one-line out_of_scope entry (id +
    testid + pin), unpinned entries still carry in full. Companion gate
    commit `953e602` (generator + selftest + regenerated manifests).
  - Runtime check: with a backend-only inventory the 46 ui testids index
    as one-liners; with the owner file in inventory they ride in full.
  - Selftests: 289/289. No product files changed, no test bytes staged —
    DELTA-v86 is purely the 46 ui contract ids.
  - Verified during the audit (held): every other EM/coder context load is
    already milestone-scoped (D-119 node-ids, the D-120 pin gate for contract ids, routes/
    schemas/errors pins since v83); the CEO's "path A/B" question needs no
    decision — the TPM-seat backfill is the D-120 design itself and pins
    already existed; the residual 8,203 B of unpinned ui testids is what
    v86 just closed.

## Milestone-trim arc — CLOSED 2026-08-07 (bounded verdict, stop condition)

**Scope:** milestone-trim audit → validation → back-port → verification.
The audit bounded: delta artifacts, runtime wiring, back-port drift,
bidirectional drift, the manifest-propagation bug, and the D-121/D-112
doc-prose classes.

**Verified against the tree (not asserted):**
- 291/291 selftests green (blueprint); 5/5 update-template tests.
- Trim machinery: zero code drift; both repos byte-in-sync
  (`check-drift.sh`, `phase-gate.sh manifest HEAD` green at every stop).
- The manifest-propagation fix (`daa24c7`) end-to-end proven on a
  throwaway child clone: apply, re-run no-op, manifest-only-drift branch.
- D-121 doc class: zero hits. D-112 completion-criterion class: zero hits
  (exhaustive case-insensitive sweep; historical records left verbatim).

**Audit boundary (explicit):** docs are NOT mechanically gated. The class
is closed by sweep, not by a gate; a future decision can re-seed drift.
Decision on guard (guard-as-warning vs skip) is the CEO's, recorded in
CURRENT.md when made.

**Next trigger (the only forward item):** the next real milestone freeze —
the trim's end-to-end lineage test (plan → coder → gates → verdict).
Nothing to run until a milestone exists; v86 is metadata-only.

**Stop condition:** no further doc-sweep passes unless (a) a guard fires,
(b) a new decision lands, or (c) the lineage test surfaces a defect.

**REOPENED 2026-08-08 — the lineage test found the next defect while
still pre-milestone:** audit against the LIVE frozen data found
DELTA-v87.json carrying **58 changed_tests / 0 changed_files** for M35's
two-comment-line UI milestone — 6 pinned M35 tests (the only ones in
`contracts.test_mapping`) + 52 relabeled leftovers of the same test file
(the D-116 shape-flip class). File-granular `changed_tests` are a
file-scope, not a milestone; `_hit_task_ids` invalidation and the
full-emission EM scope shipped all 58. **Fixed same day (D-130, rolled in
via template-update 6da4beb→b39bb08):** `validate-plan.py` now owns ONE
producer — `milestone_scope_ids()` (raw `changed_tests` ∩ frozen
`test_mapping` families, parametrization-stripped, plus the D-124
staged-file repair; inert when the mapping is empty) — and all three
consumers use it: `--subtree-scope` (map_nodeids + invalidation),
`--affected` (task-state reset), and orchestrate's full-emission
`--milestone-scope` (the inline union heredoc is gone). Verified live:
`--milestone-scope DELTA-v87.json` → **58 → 6**; selftests 315 pass in
both repos.
 
**Next trigger (updated):** the next REAL milestone freeze with a
test_mapping — after the node-scope fix, the first full end-to-end line
is a fasting data-driven milestone (the staged model-registry item),
which also re-proves plan → coder → gates → verdict on the sliced scope.
Nothing to run until a milestone exists.

**Decision made 2026-08-07 (CEO): guard-as-warning.** The doc-consistency
guard was built: `scripts/doc-consistency.sh` (enumerated retired-token scan
over enumerated state-describing docs), wired into the pre-commit hook as
non-blocking (D-115: prose has zero runtime blast radius), synced from
blueprint `23fbe0a` via `[template-update f684a16]`. Its first run caught
this repo's `README.md:61` (D-121 class) — a file on no sweep list. The
guard is warning-only by design; it can never fail a commit.

## Ledger alignment 2026-08-07 (record)

DECISIONS.md was realigned with the blueprint's (`641736a`/blueprint
`71d7404`): both ledgers now agree number-for-number (blueprint renumbered
its container/relabel/size entries to D-123/124/125; this repo back-ported
D-108..D-111, D-113..D-115, D-123..D-125). The "EM prompt context trim"
results section's D-124 designation was removed — that decision was never
entered, and D-124 now means the node-id relabel decision; when it is
logged it gets a fresh number. Guard rule recorded in the correction log:
code back-ports carry their DECISIONS entries.

## Metrics layer 2026-08-07 (record)

D-126 landed (blueprint `cfa8fba` → this repo via `48f8a31`): the metrics
layer (`scripts/metrics-report.py`, mirror D-126 in the ledger above) is
now live in both repos. Per-milestone rows land in
`.pipeline-state/logs/metrics.tsv`; `--evidence` prints the block a D-115
retirement entry must cite. Report only, never a gate. When this repo next
runs a real milestone to `[success]`, record its row and close the D-115
admission-data gap.

## Metrics durability fix 2026-08-07 (record)

The original sink (`.pipeline-state/logs/metrics.tsv`) was inside the
success teardown's `rm -rf .pipeline-state` — the row could never
accumulate and the milestone's data died with it (D-108 class, correction
row logged). Fixed same day via template update: sources are now only
post-teardown-durable artifacts (`.measurement/counters`,
`.measurement/timings-*.tsv`, spec-tagged `.em-archive`, committed flake
ledger), output is `.measurement/metrics.tsv`, and the success path records
each milestone's row automatically (`|| true`). The next `[success]` run
will emit its row with no manual step — then the ≥3-milestone accumulation
for the first real D-115 retirement (todo 7) is possible.

## Sandbox privilege property 2026-08-08 (record)

D-127 (mirrored from blueprint `fb9fa84`): the sandbox has run as non-root
`agent`/1000 since the template bootstrap — verified live in the dev-vm
(`sandbox-run.sh -- sh -c 'id -u'` → 1000, CapEff empty, no-new-privileges).
The M29 backlog premise ("container runs as root") was wrong; the incident
was macOS-vs-Linux psutil semantics. What was genuinely missing was
mechanical proof — the constraint-2 verifier checked mounts/network but
never the process user. Check 6 now asserts non-root at every
verify-sandbox-in-vm run. BACKLOG.md item retired with the correction
recorded.

## Results

  Delta-mapped frozen tests green against spec v98 — feature done (verdict scope: mapped tests only, D-112). Feature built and validated.

## Results

  Delta-mapped frozen tests green against spec v99 — feature done (verdict scope: mapped tests only, D-112). Feature built and validated.

## Results

  Full frozen TPM suite green against spec v99 (on-demand regression check, D-112). Feature built and validated.
