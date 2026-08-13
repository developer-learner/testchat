# 2026-08-13 — Lane-A brief: suite parallelization (C) + selfcheck (B) + python pin (D)

Conductor-authored work allocation for the hermetic cloud lane (Lane A),
folded into `project-trail/` per the division-of-labor contract so the
operational record outlives the session. Costed decisions behind it:
`project-trail/2026-08-10-review-remediation-closeout.md` (trail notes +
lane env model), plus the CEO-briefed criticality table (C high, B medium,
D low).

## Lane identity (verbatim operating contract)

Hermetic cloud lane. No host reality: no `:8000`, no
`/Users/arc.elixir/*`, no live servers — the suite's stub is the only
service. Lane runs playwright 1.56.0 against container browser 1194
(pinned = 1.61.0/1228); lane suite results are behaviorally indicative,
NOT authoritative. Phase-gate hook is not wired (`core.hooksPath` unset) —
reproduce gate checks by hand.

## Allocated work

**Base:** `git fetch` then branch off `origin/main` — `claude/lane-a-infra`.

**Item C (primary) — suite parallelization:**
1. Add `pytest-xdist` (pin a current stable version; record choice +
   reason in the report) to `requirements.txt` and to the pip-toolchain
   line in `Containerfile`.
2. Wire `-n auto --dist=loadfile` with the suite's JSON report emitted
   only from the coordinator worker into the CI test job
   (`.github/workflows/ci.yml`; do not weaken `--cov-fail-under`).
3. Prove it: (a) baseline full run WITHOUT `-n` — green; (b) full run WITH
   `-n` — green; record before/after wall time (`pytest --durations=20`);
   verify no port collisions (conftest allocator is per-process — each
   worker self-allocates; confirm empirically).
4. Do NOT touch `scripts/sandbox-run.sh` or orchestrate wiring — host-
   synced to blueprint, mine to wire.

**Item B (ride-along) — `scripts/lane-selfcheck.py`:** asserts environment
== pins, fails closed: playwright package version read from
`requirements.txt`; expected browser revision read from the installed
playwright wheel's `browsers.json` (never hardcoded); python major.minor ==
3.12; pytest version pin. Prints PASS/FAIL per check; exit non-zero on any
failure. Test in-container (expect FAIL on python unless container is
3.12 — record actual output).

**Item D (ride-along):** add `.python-version` containing `3.12`; one
README line under Commands: "dev venv: pin `3.12` via `.python-version`".

**Scope fences:** never `docs/DECISIONS.md`, `.template-version`,
`CONVENTIONS.md`, `.approved/`, `frozen-manifest`, or any `tests/`. One
commit per item; any commit touching a manifest-pinned file must run
`scripts/regen-manifest.sh scripts/.manifest-project` in the SAME commit
and diff to confirm only intended hashes moved; gate ok reproduced by hand.

**Deliverable:** push `claude/lane-a-infra`; report = commit list +
before/after suite numbers (with and without `-n`), the pytest-xdist
version chosen and why, selfcheck output, and an explicit cannot-prove
list: browser-class equivalence under xdist (browser is 1194), sandbox
image rebuild, CI green — host verifies all three.

## Post-arrival host verification (conductor)

1. C: D-50 sandbox image rebuild (Containerfile/requirements change
   self-triggers), sandbox full-suite wiring, CI green, and TWO full green
   host runs on the matching browser.
2. B: commit with manifest re-pin + gate; run on host — expect the python
   3.14 flag (day-one catch).
3. D: trivial review.