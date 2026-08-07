# Contracts entry→file pin — spec-delta proposal for the TPM seat

**Status:** DRAFT for the TPM seat (2026-08-06, session of D-116..D-119).
**Author of the requirement:** CEO-directed context audit — "EM and coder
artifacts should be diff-relevant to the task, no good-to-know full-load
information."
**Blocked on:** this proposal's refreeze. The EM contracts-trim (below)
cannot land before it.

---

## Why this exists (the audit chain)

The EM plan calls still ship the full `contracts.json` (74 entries, 19.6KB)
at every plan emission and re-plan, because the EM composes Rule-8 briefs
("exact signatures, exact inputs/outputs") whose signature material lives
only in contract entry bodies. The D-116/D-119 trims removed everything else
from those calls; contracts is the last full file, and it is full precisely
because **no mechanical key connects a contract entry to the file that owns
it**. Verified 2026-08-06: 0 of 40 object entries (routes 15 / schemas 21 /
errors 4) carry a `file` field, the schema has no such property, and v82's
`test_mapping` is absent. Trimming before the pin risks the EM composing a
brief that contradicts a contract it can no longer see — the exact failure
class the correction log warns about.

## The required change (one TPM freeze)

### 1. Schema — `scripts/schemas/contracts.schema.json`

For each of `routes`, `schemas`, `errors` (the object-entry arrays):

- add an optional property:
  ```json
  "file": {
    "type": "string",
    "pattern": "^src/.*\\.py$",
    "description": "The source file that owns this contract entry — the file whose code must satisfy it. Used to slice the contracts for the EM's per-milestone context."
  }
  ```
- **`additionalProperties: false` stays in force** — the pin is explicit,
  not free-form.
- `required` arrays stay as-is (id/method/path etc.). Do NOT make `file`
  required in the schema; the freeze-time check below is the enforcer, so a
  staged delta can add the pin to only the entries it touches.

### 2. `entry_points` need no tag (self-pinning)

`entry_points` are dotted strings (`"src.main:app"`, `"src.services.llm"`).
The owning file is mechanical: strip any `:object` suffix, convert dots to
slashes, append `.py` → `src/main.py`, `src/services/llm.py`. The slice
derives these; do not restructure the array.

### 3. One-time backfill of the 40 object entries

The same freeze that lands the schema change must add `file` to every
existing route/schema/error entry (15+21+4). For testchat v82:

- `routes`: the file whose handler serves the route (e.g.
  `route:GET /` → `src/main.py`, `route:POST /api/v1/chat` →
  `src/api/chat.py`, model routes → `src/api/models.py`, threads/settings/
  websearch/storage routes → their `src/api/*.py` files).
- `schemas`: the file that defines or consumes the schema (e.g.
  `schema:ChatRequest` → `src/api/chat.py`).
- `errors`: the file that raises the error (e.g. `error:422-validation` →
  the route handler's file).

A wrong pin is worse than no pin (it silently shrinks the EM's context to
the wrong slice) — when ownership is genuinely split across files, choose
the file whose code must satisfy the entry, and say so in the delta's
`## Changed files` notes so the EM prompt can name the ambiguity.

### 4. Freeze-time check (gate-owned, not prose)

`scripts/check-spec-delta.py` gains a check: every NEW or CHANGED
route/schema/error entry in a staged delta must carry a `file` matching the
pattern. Carried entries are exempt per freeze (backfill happens exactly
once, in this proposal's freeze; the exemption can be removed once the
standing contracts carry the pins).

## The payoff (NOT in this freeze — orchestrate-side, post-pin)

A `contracts-delta` generator alongside `standing-summary.py` (D-116):
`contracts.json` entries whose `file` (or derived `entry_points` path) is in
the milestone's `contracts.files` inventory become the EM's `contracts`
context block; everything else stays out. A milestone touching no pinned
entries ships the flat id list only (already printed via `contract_ids`).
This is the mechanical slice that makes the EM's contracts load equal to
its actual need, closing the last full-load site. It must be an independent
change after this freeze validates the pins, with its own selftests.

## Deliverable format

Standard TPM delta reply (sentinel-wrapped, `scripts/tpm-unpack.sh` →
`scripts/refreeze.sh`): `scripts/schemas/contracts.schema.json` is a
repo-lane file and does NOT ship through the TPM artifact allowlist —
the TPM's delta delivers `contracts.json` (with all 40 pins) and the
conductor lands the schema edit + check-spec-delta.py check as the
accompanying control-plane change in the same freeze session, per the
check-test-surface/spec-delta lane rules.
