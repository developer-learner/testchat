# CURRENT.md — Session Notes

> Human-facing status page, NOT the spec. Frozen spec lives in
> scripts/.approved/ and changes only via scripts/refreeze.sh (D-31).

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
