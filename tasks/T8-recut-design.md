# T8 — recut Testchat's router seams onto Vortex's real v26 surface

**Status (2026-09-01): v115 spec DRAFTED and staged — all refreeze
preflights green.** The frozen-spec artifacts (PRD delta AC-175..AC-181,
ERD-DELTA v115, contracts delta, 20-test oracle) are staged in
`scripts/.approved/incoming/` and durably recorded in
`tasks/T8-v115-spec-draft/`. The oracle against the unmodified code is
**8 failed / 12 passed** — the 8 failures are exactly the new-behavior
pins (full ready set, dynamic routing, constant retirement, AC-179
race); the 12 passes are regression guards. The freeze + build still
need the one-live-run-at-a-time memory/RAM window (Linux dev VM); the
run is `scripts/refreeze.sh scripts/.approved/incoming` (D-121:
green preflights = auto-apply) followed by `scripts/orchestrate.sh`.

**Design prep, 2026-09-01 (TPM).** Not the frozen spec — the freeze-first flow
(PRD/ERD/tests → `refreeze.sh` → build) authors that when the milestone runs.
Precedes T9 (the deployment cutover; see `T9-cutover-design.md`). T8 is a
code milestone; the build fires the local coder and so needs a memory/RAM window
(one-live-run-at-a-time) — it is not started by this note.

## Why a recut is needed

The v114 router seams (`src/services/models.py:421-468`) were built against an
**assumed single-model router**: `router_models()` hardcodes one `ROUTER_MODEL_ID`
and returns it only if present, and `is_router_model()` matches that one id.
Vortex v26 actually advertises the **full dynamic set of currently-ready models**.
So the transport is right but the model-set logic is wrong for the real surface.

## Vortex v26 surface (verified from source)

- `GET /v1/models` → `{"data": [{"id": <public_id>, "owned_by": <runtime>, ...}]}`,
  and it lists **only `manager.client_ready()` entries** — i.e. it is already
  *ready-only* by construction (`vortex/src/vortex/app.py:62-77`). The T9
  ready-only picker therefore needs no extra filtering on the Vortex group.
- `POST /v1/chat/completions` → **404** when the model is not loaded/ready
  (`app.py:78-83`); otherwise streams the upstream SSE, inspecting upstream
  status before returning 200.
- Load / unload / catalog / RAM live on a **separate management surface**
  (`/api/catalog`, `/api/status`, `/api/models/{id}/load|unload`,
  `/api/operations/{id}`) + the dashboard at `/`. Testchat must NOT drive these;
  they are the target of T9's "Manage models in Vortex ↗" link.

## The recut delta (acceptance-criteria seeds)

1. **All ready models, not one.** `router_models()` returns one `{id, source:
   "router"}` per id from `_router_probe()` — the full ready set — instead of
   filtering to `ROUTER_MODEL_ID`.
2. **Dynamic membership.** `is_router_model(id)` is true iff `id` is in the live
   `_router_probe()` set (any ready Vortex model), not `id == ROUTER_MODEL_ID`.
3. **Retire the placeholder.** `ROUTER_MODEL_ID` (single-model stand-in) is
   removed; nothing downstream may assume a fixed router-model id.
4. **404 = not-ready, not an error.** A Vortex 404 on chat (model unloaded
   between listing and send) surfaces as "model not ready in Vortex" and offers
   the local fallback — not a 500. Feeds T9 AC4 (offline/fallback).
5. **No change to transport seams.** `router_chat_endpoint()` (base +
   `/v1/chat/completions`) and `_router_probe()` (parse `.data[].id`) already
   match v26 — the recut must not churn them.

## Unchanged / out of scope

The local `SCRIPT_MODELS` + LM Studio path (`models.py` process-lifecycle code)
stays as the fallback supply. T8 aligns the router seams only; making Vortex the
**primary** source and the picker ready-only is T9.
