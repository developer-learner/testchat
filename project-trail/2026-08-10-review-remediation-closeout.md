# 2026-08-10 — Review-remediation batch closeout

Conductor-authored closeout for the 8-finding review remediation batch
(handoff: `2026-08-10-review-remediation-handoff.md`). Merged to `main`
via PR #1 (`0b72cc3`, merge commit). Everything below passed host
acceptance; CI (selftest + test) green on the merged head.

## Division of labor (post-labor contract)

Batch executed across three lanes. Rule: hermetic-draftable work goes to
cloud LLM lanes (hermetic environments — identical fs/git/images); anything
requiring host-exclusive truth (live server on :8000, real fs, real
ports) is host-verified by the conductor regardless of draft origin.

- **Lane 1 (cloud, existing session):** T2 identity sidecar (`a309c05`),
  T4 non-blocking lists (`0cffce4`), plus T9 doc touch-ups
  (`20f24b0`, README cherry-picked to `main` as `6c520d3`).
- **Lane 2 (cloud, new session):** T7 dotenv (`8f1c479`), T6 localStorage
  model store (`1322028`), T8 ✓-glyph removal (`71058db`).
- **Host (conductor):** T1 test isolation (`deb5105`), T1-teardown leak
  fix (`dd9c652`), T8-conftest port allocator (`796abb4`), T9 `ruff format`
  (`69b37a2`), all host verification, reconciliation merge (`7e9aee9`).

Verification never delegated: every lane output re-verified on the host
against the live `omlx-server` (PID 44751, `127.0.0.1:8000`), which was
never killed.

## Per-task verdicts

- **T1 (P2-4, test isolation)** — DONE, `deb5105`. Root cause: fixture
  repointed only the target registry entry; the load path's eviction pass
  probes other entries' ready_urls (nemotron `:8600`, ds4 `:8000`,
  ds4-0731 `:8005`). Host live server caused AC-163 refusals; container
  stayed green — environment-differential defect. Fix: one shared per-test
  port map; each entry isolated exactly once. Host suite green WITHOUT
  `DS4_URL` overrides, manifest re-pinned.
- **T1-teardown (leak fix)** — DONE, `dd9c652`. Autouse teardown now
  unloads every registry entry. Was leaking ~25 `_SERVER_SRC` servers per
  suite; after fix: 0 leaked.
- **T2 (P1-3, process-identity)** — DONE, `a309c05` (Lane 1, host-verified).
  Sidecar records PID + server start-time; unload refuses foreign
  processes, AC-163 intact. Live-safety proven against PID 44751:
  refused, not killed. Real `ds4-server` exec path blocked by broken
  symlink `/Users/arc.elixir/dev/ds4/ds4flash.gguf` (dangling → model
  missing) — flagged, not a batch defect.
- **T3 (P2-5, load lock)** — DONE (earlier). Re-verified live: unload
  against real server refused; suite green with it running.
- **T4 (P2-6, non-blocking lists)** — DONE, `0cffce4` (Lane 1,
  host-verified). `get_models`/`get_model_catalog` async→def; measured on
  real uvicorn: `/api/v1/models` 6.06s while concurrent `/` returned
  0.001s. Ships test-less — Lane 1's two test designs flaked under
  full-suite load; no-test call accepted.
- **T5 (P2-7, websearch env robustness)** — DONE (earlier, `f543de4`).
- **T6 (P2-8, per-thread model store)** — DONE, `1322028` (Lane 2,
  host-verified). localStorage `THREAD_` store; script-only eject gating;
  2 new UI tests, no new testids.
- **T7 (P1-2, .env)** — DONE, `8f1c479` (Lane 2, host-verified).
  `load_dotenv` before router imports; `.env` NEMOTRON_URL picked up.
- **T8 (P2-9 + conftest)** — DONE. `71058db` ✓-glyph removal (Lane 2);
  `796abb4` session-unique port allocator (host, replaces fixed
  8971/8972); `f569528` concurrent-load fix (earlier).
- **T9 (format)** — DONE, `69b37a2`. `ruff format src/` (9 files), 20
  pinned test files untouched, manifest gate ok. Final acceptance: **212
  passed / 0 failed** in 5:13, server alive+same PID, 0 leaked.

## End-of-batch acceptance (host, no overrides)

- Full suite: 212 passed, 0 failed (313s).
- `127.0.0.1:8000` alive + same PID before/after: YES.
- Leaked processes: 0.
- `ruff check src tests`: clean.
- `mypy --explicit-package-bases src/`: clean in cloud lanes; NOT
  runnable on host (command not found) — flagged, no functional gap.
- CI on merged head: selftest pass, test pass (container suite green).

## INV-4 — refreeze flag

`tests/test_ui_settings.py:22-23` locates testid `settings-status`, which
is not in `contracts.ui`. Pre-existing (introduced host-side at
`7bfc622`), discovered during T6 verification. NOT edited this batch —
deferred to the TPM refreeze lane per CEO decision ("merge after T9,
refreeze for INV-4").

## Trail notes

- Lane 1's T9 branch (`claude/lane1-t9`, `20f24b0`) carried no unique src
  content (ruff-format deterministic, byte-identical to `69b37a2`); its
  README touch-up cherry-picked to `main` (`6c520d3`). Branch left as-is.
- `claude/lane2-t7-t6-t8` and `host/lane3-conftest` are merged artifacts;
  kept for audit.
- Post-merge drift incident (worktree left on `claude/lane2-t7-t6-t8`;
  one commit landed there, push rejected) — recovered by reset + recommit
  on `main`. No content lost; no force-push.
- **Lane-1 hermetic-env model corrected post-closeout** (lane
  self-verified): toolchains NOT pre-installed (entry runs
  `pip install -r requirements.txt`); browser toolchain is container
  Chromium build 1194 vs pinned `playwright==1.61.0` (wants build 1228,
  proxy blocks download) — lane runs playwright 1.56.0, so Playwright
  drafts are behaviorally accurate but not byte-identical; the phase-gate
  hook is NOT wired in the lane (`core.hooksPath` unset) — the lane
  reproduced gate checks by hand (regen-manifest.sh, check-test-surface.py,
  manifest diffing); third blind-spot category named: harness-only limits
  (T4's `TestClient` per-request loop made a stable suite-RED
  unachievable — fix shipped with in-isolation RED/GREEN and an explicit
  "confirm on host" flag). Allocation blurb updated; see CLAUDE.md
  correction log.
