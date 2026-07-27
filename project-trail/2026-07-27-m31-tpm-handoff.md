# M31 handoff — TPM role vacated

**Date:** 2026-07-27
**Reason:** CEO removed me from TPM after five sequential spec-defect refreeze cycles (v60→v64) with zero forward progress on M31.

## Current tree state

| Location | Branch | HEAD | Notes |
|---|---|---|---|
| `~/dev/testchat` | main | `5b8c56e` [refreeze v64] | pushed to origin |
| `~/dev/testchat-mlx4bit` | m31-mlx4bit | `5b8c56e` | reset to v64; last run halted at plan gate |
| `~/dev/testchat-mtplx8bit` | m31-mtplx8bit | `7d756d0` [refreeze v63] | **untouched, still at v63** |

Uncommitted on main: `tasks/plan.json` (stale planner output, erd_version 58, not part of freeze). Untracked: `project-trail/2026-07-26-blueprint-findings.md`, `project-trail/2026-07-26-m31-handoff.md`, and this file.

## Environment

- **Lima `dev-vm`:** started (was Stopped before session; now Running).
- **mlx-serve:** up on `127.0.0.1:11234`, `ddalcu/Qwen3.6-27B-4bit-MTP-MLX-Serve` loaded ready.
- **mtplx:** not verified this session (memory says port 8001, seat = `mtplx-qwen36-27b-optimized-quality`, must be started from MTPLX app).
- **testchat app:** not touched; runs on 8080 per `.claude/launch.json`.

## Refreeze arc — what each version broke

| Ver | What I tried | Why it halted |
|---|---|---|
| v60 | initial M31 spec | inverted no-edit default made every existing file no-edit |
| v61 | fix no-edit | brittle grep oracle (`[data-active='true']` vs `="true"`) — 4 coder strikes |
| v62 | fix oracle | added `current-chat.css` as new file — nothing could `<link>` it (index.html outside delta) |
| v63 | fix asset | spec-only refreeze produced empty delta (`refreeze.sh` never diffs `ui` scope) |
| v64 | fix delta by dropping CSS file, injecting styles in app.js | T7 brief hit 2697 chars, EM cap is 2500 — plan gate halted after 2 revisions |

## v64 halt — the specific failure

Plan gate:
```
PLAN GATE FAIL: task T7: brief is 2697 chars (max 2500) — split the task or tighten the brief (Rule 8)
```
T7 = `src/static/app.js`. Brief bundled 5 M29 carry-forward items + 6 M31 items + item 12 (my v64 style-injection addition). Retry will regenerate the same overshoot — halt is structural, not variance.

Recovery mechanism (per orchestrate diagnostic): `rm .pipeline-state/plan_revisions*` in the worktree refreshes budget if fix is outside the spec. **Fix is inside the spec**, so the correct path is v65 not a retry.

## v65 direction — per CEO, not to be executed by me

Two design principles I violated across v60–v64:

1. **Split features into their own files.** Blueprint enforces one task per file, so scope reduction happens by *adding files*, not compressing briefs. `index.html` is editable (only `markdown.js`, `rain.js`, `style.css` are in `no_edit_files`) — outside-the-delta ≠ no-edit. I collapsed the CSS back into app.js in v64 when the right move was to widen the delta.

2. **The coder emits anchored SEARCH/REPLACE edit blocks (`apply-edit-blocks.py`), not full files.** The 2500-char cap is on the brief (the spec of edits), not on the coder's diff. Overshooting the cap signals scope-per-file is wrong, not that prose is wrong.

Correct v65 sketch:
- Add `src/static/current-chat.js` as a new file in `contracts.files`.
- Move items 6–11 (header title, inline rename, sidebar highlight, refresh-to-newest, cross-source rename sync, text safety) into that new file's spec.
- Put `index.html` in the delta so `<script src="current-chat.js">` can be added.
- app.js brief shrinks to M29 carry-forward + one line calling the new module on init/switch.
- Style block can live inline in current-chat.js — separate CSS file is optional and only worth it if size warrants.

## Sandbox invariants (do not re-derive)

- Coverage floor **79**, not 80 (0.3pt platform delta straddles 80).
- Real app port **8080**, not 8000 (README quick-start is deliberately stale per `c4710cc` revert).
- `orchestrate.sh` runs only inside Lima `dev-vm` (`limactl shell dev-vm`), tree live-mounted at same path.
- Per-run seat swap: `SWBP_EM_MODEL`, `SWBP_CODER_MODEL`, `SANDBOX_LLM_HOST=host.lima.internal`, `SANDBOX_LLM_PORT` — never write `models.env`.
- Never wipe `.pipeline-state/tasks/` — orchestrate's re-freeze detection resets affected tasks itself.

## What I will NOT do without explicit re-engagement

Draft v65 (or any refreeze), stage or push spec changes, restart the pipeline, or offer another TPM opinion on M31 scope. Assisting from outside the role (reading state, running commands, answering direct questions) is fine.
