# CURRENT.md — Session Notes

> This is the human-facing status page, NOT the spec. The PRD, ERD, contracts
> and test suite live frozen in `scripts/.approved/` + `tests/` and change
> only via `scripts/refreeze.sh` (D-31). Update this file at the start and end
> of every working session; halt notes (Rule 4) land here.

---

## Active Feature

**Feature:** M3 — Streaming SSE
**Frozen spec version:** v3 (frozen)
**Orchestrator state:** in_progress (19/19 tests green, CEO acceptance pending)
**Branch:** `main`

---

## Latest Results

**M3 (Streaming SSE)** — built and validated. All 19 frozen tests pass.
- `src/services/llm.py` — `stream_reply` generator: urllib raw socket reads (`response.fp.read1(4096)`), SSE line parsing, `[DONE]` sentinel, error handling. `<think>` block stripping removed (think content streams to frontend for low-latency first token).
- `src/api/chat.py` — `StreamingResponse` wrapping `stream_reply` as `text/event-stream` with `token`/`done`/`error` SSE events.
- `src/static/index.html` — Consumes SSE stream via `ReadableStream.getReader()`, renders tokens with inline `<think>` block dimming.
- Latency fix: replaced httpx with urllib `response.fp.read1()` — first-token latency dropped from ~24s to ~1.3s.
- Think-block stripping removed (was causing 18s+ delay before any visible output since qwen3.6-27b emits long thinking traces).

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
- M4: Conversation history — full context sent to LLM

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
