# CURRENT.md — Session Notes

> This is the human-facing status page, NOT the spec. The PRD, ERD, contracts
> and test suite live frozen in `scripts/.approved/` + `tests/` and change
> only via `scripts/refreeze.sh` (D-31). Update this file at the start and end
> of every working session; halt notes (Rule 4) land here.

---

## Active Feature

**Feature:** M5 — Nemotron model management + routing
**Frozen spec version:** v7 (frozen)
**Orchestrator state:** done (58/58 tests green)
**Branch:** `main`

---

## Latest Results

**M5 (Nemotron model management + routing)** — built and validated. All 58 frozen tests pass.
- `src/services/models.py` — `list_models`, `is_nemotron_loaded`, `load_nemotron`, `unload_nemotron` with subprocess management and timeout/grace cleanup.
- `src/api/models.py` — FastAPI router: `GET /api/v1/models`, `POST /api/v1/nemotron/load` (503 on error), `POST /api/v1/nemotron/unload`.
- `src/api/chat.py` — model routing: `model` field in `ChatRequest`, `endpoint_override` to Nemotron endpoint when model="nemotron"; 422 if nemotron selected but not loaded. Fixed `NEMOTRON_CHAT_ENDPOINT` import (was from wrong module).
- `src/main.py` — registered models router.
- `src/static/index.html` — model selector dropdown populated from `GET /api/v1/models`, Load/Unload Nemotron buttons, `model` field in chat POST, selector locked after first message.

CEO acceptance pending (D-44).

---

## Escalations In Flight

None.

---

## Notes / Context

Milestone plan:
- M1: Echo chat — ✅ done
- M2: Live LLM integration — ✅ done
- M3: Streaming (SSE) — token-by-token response — ✅ built (CEO acceptance pending)
- M4: Conversation history — full context sent to LLM — ✅ built
- M5: Nemotron model management + routing — ✅ built (CEO acceptance pending)

---

## Definition of Done (per feature)

Mechanical checks:

- Full frozen suite green (`scripts/orchestrate.sh` exit 0)
- `docs/ARCHITECTURE.md` updated if structure changed
- `docs/DECISIONS.md` updated if a non-obvious choice was made
- No linter errors (`ruff check src/`)

The one judgment check (D-44 — the CEO's gate, never skipped or delegated):

- **CEO has used the running prototype and accepted the milestone.**
  "Tests green" means built-as-specified; only this means built-right.
  Record the acceptance here with a date.

Then: branch merged to main; entry moved to `BACKLOG.md` completed table

## Results

Full frozen TPM suite green against spec v3. Feature built and validated.

## Results

Full frozen TPM suite green against spec v5. Feature built and validated.

## Results

Full frozen TPM suite green against spec v7. Feature built and validated.

## Results

Full frozen TPM suite green against spec v9. Feature built and validated.
