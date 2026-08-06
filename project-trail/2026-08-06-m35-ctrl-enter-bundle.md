# M35 — composer keyboard behavior: TPM bundle + conductor handoff (2026-08-06)

## Business intent (CEO)

Invert the composer keyboard mapping: **Enter inserts a newline**, **Ctrl+Enter
(and Cmd+Enter on macOS) sends**. Nothing else changes.

## Bundle (staged in `.tpm/outbox/`)

| Artifact | What changed |
|---|---|
| `PRD.md` | AC-152..AC-155 added (Enter=newline, Ctrl+Enter=send, empty guard, placeholder). AC-140/142/144/148 reworded, meaning-preserving, with "such that" clauses (the S5 lint flags them as legacy debt — the D-68 pattern on the spec side) |
| `ERD-DELTA.md` | New behavioral delta, D-107 shape, `check-spec-delta.py` verdict: **behavioral** |
| `contracts.json` | v80: `files` = app.js + index.html; `smoke_checks` = app.js landmarks only; everything else byte-copied from v79 |
| `tests/test_ui.py` | 1 update (`:956` Enter→Control+Enter, the ONLY Enter-send test in the suite — the other 9 `press("Enter")` sites are rename-input commits, AC-114, untouched) + 5 new tests (AC-152..155: plain-Enter newline, Ctrl+Enter send, Cmd+Enter send, empty no-send, placeholder text) |

## Validation already run (TPM side)

- S5 lint green on both PRD.md and ERD-DELTA.md (`check-ac-postconditions.py`)
- D-107 delta check green (behavioral)
- contracts.json valid JSON, schema shape preserved from v79
- 6 delta tests are red against the current app.js — D-75 red-before-green is
  expected to fire exactly as designed

## Conductor (other LLM) — what to do

1. Review: `scripts/refreeze.sh .tpm/outbox --diff` (or the interactive diff)
   — you own the diff review + approval per the CEO's arrangement (D-42
   `--approve <hash>` behind your ask-prompt; CEO is backstop, not reviewer).
2. Install: `scripts/refreeze.sh .tpm/outbox` — expect the D-75 red-check to
   pass (delta tests red pre-implementation).
3. Run: `./scripts/orchestrate.sh` — EM (mtplx, port 8001) plans against
   contracts v80; 2 tasks: `src/static/app.js` first, `src/static/index.html`
   second (the required DAG is stated in the ERD-DELTA).
4. If a halt exposes an orchestrate-side bug: orchestrate.sh is my lane —
   hand it to me, do not edit it.

## Measurement expectations (my instruments, mine to read after the run)

- `.measurement/counters` — exit row (rc/phase/spec/revisions/elapsed),
  `identical_retry`, `spec_defect` firings; `timings-<ts>.tsv` copies
- After-measurement vs baseline `2026-08-06-phase5-baseline-instrumentation.md`
  (acceptance: ≤2 refreeze cycles, 0 S1–S7 defects, storm < 30 min,
  identical-retries ≤ 1)
- Live watch closure: closure-repair/contract-repair firings reconstructed
  offline from `.em-archive/` (validate-plan.py `--repair-*` replay per
  archived `reply.json`)
- Phase 4 gate re-check: post-run archive re-measurement per
  `2026-08-06-phase4-preregistered-gate.md` (method + criteria unchanged)
