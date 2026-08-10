# 2026-08-10 — Review-remediation execution handoff

Conductor-authored handoff spec for the 8-finding review remediation batch
(see review classification: P1-1/P1-2/P1-3 critical, P2-4..P2-9 medium,
P3-10 + conftest + docs + formatting trivial). Executed direct-lane per
D-132 (route pipeline-vs-direct by size and determinism, never the
bug/feature label — see docs/DECISIONS.md).

## Preamble (read first)

- **Scope:** 9 tasks below, all direct-lane (D-132). No EM/coder, no VM,
  no milestone. All host-side.
- **Authorization:** T1 and T8 touch hash-pinned test files. The CEO has
  authorized these edits direct (`--no-verify`, `7bfc622`/`f569528`
  precedent) for this batch. Every commit that touches `tests/` MUST update
  the sha256 entries in `scripts/.approved/frozen-manifest` (regen with
  `scripts/regen-manifest.sh scripts/.approved/frozen-manifest` if
  supported, else `sha256sum` + edit, keeping the `hash  path` format and
  sorted order) so the gate is green for all later commits.
- **Commit recipe per task:** (1) write/adjust the regression test first,
  run it — must be RED; (2) implement the fix; (3) repin frozen-manifest;
  (4) commit. `--no-verify` only on commits whose test-file edits are
  authorized (T1, T8); all other commits must pass the phase-gate. Never
  touch `scripts/`, `.template-version`, `CLAUDE.md`,
  `docs/DECISIONS.md`, `.manifest-project`.
- **Verification:** after each task, run the targeted tests; at T1, T3,
  T6, and the end, run the FULL suite `PYTHONPATH=. pytest -q` — after T1
  it must be green WITHOUT `DS4_URL` overrides on the host (the live
  `omlx-server` on port 8000 must never be killed). End of batch:
  `ruff check src tests`, `mypy --explicit-package-bases src/`, full
  suite, push, CI green (selftest + test + check-drift).

## T1 — Test isolation (keystone, ~15 min)

Files: `tests/test_models_api.py`, `tests/test_model_lifecycle.py`,
`tests/conftest.py`.

Method: fixtures must never probe/kill processes they didn't spawn. One
shared per-test port map (module-level fixture, each registry entry
isolated exactly once — re-configuring one model must NOT clobber another
test's isolated endpoint, which broke AC-104's eviction test in the first
attempt). Spawned servers recorded by PID; teardown kills only recorded
PIDs. Ports drawn from a shared allocator so two suites can run
concurrently. The 3 host failures must go green without env overrides.

Verify: full host suite green; AC-163 refusal test still passes;
`omlx-server` untouched.

## T2 — Identity record / unload-after-restart (P1-3, ~20 min)

Files: `src/services/models.py` + lifecycle tests.

Method: persist a sidecar record (PID + start-time + model id + port) when
the app spawns a server, so the registry survives restart. On unload:
resolve the live process by port→PID, verify start-time (recorded) AND the
existing token/basename match (`_pid_is_model_server` kept as fallback —
the frozen oracles pin it); never terminate without positive
identification. This restores unload for `run-server.sh`→`exec`'d servers
(PID changes under exec: the sidecar's PID is dead, so identification
falls back to cmdline token match of the live process). Keep AC-163's
refusal for unidentified processes intact.

Verify: spawn → restart app → unload works; unload of a foreign process
still refused.

## T3 — Concurrent-load lock (P1-2, ~10 min)

File: `src/services/models.py`.

Method: serialize the load/unload mutation path (ready-check, eviction
pass, spawn, handle update) with a `threading.RLock()` — FastAPI runs
these in a thread pool; two parallel loads must not both pass the
ready-check and spawn duplicates. Regression test: two concurrent load
calls → exactly one server.

Verify: duplicate-spawn test green (red before fix).

## T4 — Non-blocking load/unload (P2-5, ~10 min)

File: `src/api/models.py` (endpoints) + models service if needed.

Method: startup/shutdown polling is synchronous and blocks the event loop
up to ~2s. Move the blocking work off the loop (run the poll in a thread /
make the endpoints `def`→`run_in_threadpool`, same class as the AC-165
fix). Regression: during a slow load, a concurrent request completes
without multi-second delay.

Verify: concurrent-request latency test.

## T5 — Websearch fallback (P2-6, ~10 min)

Files: websearch service + chat streaming.

Method: a bad `WEBSEARCH_*` env value or an upstream shape mismatch must
degrade with the promised notice (the `error` SSE event), never kill the
whole stream. Regression: malformed env + malformed upstream response →
stream continues with notice.

Verify: targeted tests.

## T6 — Frontend correctness (P2-8, P2-9, P2-7, ~25 min)

Files: `src/static/catalog.js`, `src/static/threads.js`,
`index.html`/`chrome.js` as needed.

- P2-8: persist the per-thread model selection (localStorage) — restore on
  reload (M32 promise).
- P2-9: the eject button must not render for LM Studio models (only for
  script-model servers).
- P2-7: sanitize link targets — reject `javascript:` scheme on both render
  and click.

Verify: Playwright node-ids for these behaviors (green after fix).

## T7 — .env + .env.example pair (P2-4, ~15 min)

Files: `src/main.py`, `.env.example` (new/rewrite).

Method: call `load_dotenv()` at app startup (before config reads);
`.env.example` documents `LLM_ENDPOINT`, `LLM_MODEL`,
`LLM_TIMEOUT_SECONDS` and any other documented vars. Ship both in one
commit (the fix has no visible effect without the example).

Verify: app picks up a value from `.env`; `.env.example` matches the vars
CLAUDE.md/README document.

## T8 — Polish (P3-10 + conftest ports, ~15 min)

Files: index.html/chrome.js (`✓` removal — one line, CEO-rejected
2026-07-19, now re-adopted per this review); `tests/conftest.py` port
allocator (authorized, pinned).

Verify: targeted tests + full suite.

## T9 — Docs + formatting (last, zero risk)

`ruff format` on `src/` only (9 files); docs stale-but-harmless updates.
The 20 test files are NOT formatted (pinned; ride the next refreeze).

Verify: `ruff format --check src`, suite green.

## End-of-batch checklist

Full suite green on host (no env overrides) AND in the sandbox
(`limactl shell dev-vm` → `scripts/sandbox-run.sh -- pytest`),
`ruff check`, `mypy`, push, all three CI jobs green. Report: per-task
verdict, the frozen-manifest diff, and the authorization usage.
