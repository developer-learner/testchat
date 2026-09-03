# Design: user-understandable chat error copy (distinct plain cause + retry)

**Status:** SUPERSEDED / NOT BUILT (2026-09-03). The CEO refined the decision
to *one generic retry line for every failure, no suggestions* — shipped as spec
**v122** (AC-182; `_messageless_error()` always returns `FALLBACK_REPLY`). This
distinct-per-cause design was not implemented; it is kept only as provenance.
The generic version is the delivered behavior.
**Size:** ~1 hour. Milestone-shaped: it changes frozen product behavior, so it
goes through `scripts/refreeze.sh` (new ERD-DELTA + updated frozen tests), then
the code lands. NOT a direct patch — the current spec pins the old behavior.

## Product decision (CEO, 2026-09-03)

When a chat fails, the user should see an **error message they can understand** —
the actual cause in plain language (e.g. "The model failed to load."). Rules:

- State the cause plainly. No jargon, no internal error text.
- **No suggestions** — do NOT tell the user to "try another model", "load it",
  or "pick a local model". Just state what happened.
- Offer retry as the **only** action: end each line with "Please try again."

## Why this is a freeze, not a direct edit

Today every failure path in `src/services/llm.py::stream_reply` collapses to a
bare `("error",)` tuple; `src/api/chat.py` then shows one generic line, and the
router case adds a *suggestion*. The frozen suite pins exactly this, in two files:

- `tests/test_chat_api.py:117` and `:131` assert the error message equals the
  generic FALLBACK line on the connection-error and mid-stream paths.
- `tests/test_router_route.py:368-371` asserts the router-404 case shows
  "Model m1 is not ready in Vortex. Pick a local model or retry once it is
  loaded." — the suggestion the CEO wants removed.

Tests are TPM-authored/frozen (INV-1); they change only via `refreeze.sh`. So
this is a spec update (ERD-DELTA + updated tests staged red-before-green), then
the code.

## The change (fully designed — ready to build)

### 1. `src/services/llm.py` (entry_point) — name each cause + log it

Add five module constants (the exact user-facing strings below), give each of
the five failure paths in `stream_reply` its own constant, and add a
`logging.warning` at each path carrying the diagnostic detail for operators (the
tuple carries only what the user should read; module logger =
`logging.getLogger(__name__)`). Each path keeps its existing yield shape, but as
`("error", <CONSTANT>)` instead of a bare `("error",)`. `FALLBACK_REPLY` stays;
add the five constants to `__all__`.

| Failure path in `stream_reply` | constant | user string |
|---|---|---|
| `response.status != 200` | `ERR_ENDPOINT_STATUS` | The model failed to load. Please try again. |
| stream closes with no content (DONE sentinel, no tokens yielded) | `ERR_EMPTY_REPLY` | The model returned an empty reply. Please try again. |
| a chunk fails `json.loads` / KeyError / IndexError | `ERR_UNREADABLE` | The model sent a response that could not be read. Please try again. |
| read loop ends without the DONE sentinel | `ERR_INTERRUPTED` | The model's response was interrupted. Please try again. |
| `urllib.error.URLError` / ValueError / OSError | `ERR_UNREACHABLE` | The model could not be reached. Please try again. |

`src/api/chat.py` already relays `item[1]` when present (`chat.py:95-101`), so
real failures now show the cause with no further code change there. The UI
already renders `errData.message` (`src/static/app.js:340-349`), so no UI change.

The full ready implementation was drafted this session (llm.py rewritten with the
constants + `logger.warning` at each of the five paths); reconstruct it from the
table above — it is mechanical.

### 2. `src/api/chat.py` — retire the suggestion

`_messageless_error()` still returns the "Pick a local model…" suggestion for the
router-404 case. With llm.py always supplying a message that branch is
production-dead, but it still contradicts the "no suggestions" decision and is
still spec-pinned. Change its router-404 copy to the plain, suggestion-free
"The model failed to load. Please try again." (the error-while-ready branch's
`FALLBACK_REPLY` is already suggestion-free and can stay).

### 3. Frozen tests (staged via refreeze, red-before-green)

- `tests/test_chat_api.py`: update `:117` (connection error) to
  `ERR_UNREACHABLE` and `:131` (mid-stream/interrupted) to `ERR_INTERRUPTED`.
  Add cases pinning the other distinct causes: non-200 to `ERR_ENDPOINT_STATUS`,
  empty stream-close to `ERR_EMPTY_REPLY`, malformed chunk to `ERR_UNREADABLE`.
- `tests/test_router_route.py`: update the `test_chat_router_404_race…`
  assertion (`:368-371`) to the new plain line.
  `test_chat_router_error_while_still_ready_is_generic` (equals FALLBACK_REPLY)
  stays valid.

### 4. Freeze artifacts

- `scripts/.approved/ERD-DELTA-v122.md`: changed AC(s) for error copy —
  distinct plain cause + "Please try again", no suggestions. (No state-changing
  verbs, so no S5 post-condition clause needed.)
- `scripts/.approved/contracts.json`: `test_mapping` entries for the new/changed
  node-ids to `src/services/llm.py` (cause tests) and `src/api/chat.py` (router).
- `PRD.md`: additive only — record the error-copy behavior, supersede the old
  suggestion line in the ERD-DELTA (do not delete history; D-136).

## Verify

Host-runnable without the sandbox (TestClient + pytest_httpserver, ephemeral
ports): `PYTHONPATH=. pytest tests/test_chat_api.py tests/test_router_route.py`.
Confirm the updated/new tests are RED against current code before staging, GREEN
after the llm.py + chat.py changes land.
