# ERD-DELTA v115 — router recut: the full dynamic ready set (T8)

Freeze context: standing spec v114 (router oracle made hermetic; the
single-model router seams of v107 stand frozen). T8 recuts the router
seams onto Vortex's real v26 surface, verified from source:
`GET /v1/models` advertises the **full dynamic set of currently-ready
models** (ready-only by construction — it lists only
`manager.client_ready()` entries), and `POST /v1/chat/completions`
**404s** when the model is not loaded/ready. The v107 seams were built
against an assumed single-model router (`ROUTER_MODEL_ID`): the transport
was right, the model-set logic was not.

## Design

- `router_models()` returns one `{id, source: "router"}` per id from the
  live `_router_probe()` — the full ready set, probe order, deduplicated —
  instead of filtering to `ROUTER_MODEL_ID`.
- `is_router_model(id)` is true iff `id` is in the live probe set (any
  ready Vortex model), not `id == ROUTER_MODEL_ID`.
- `ROUTER_MODEL_ID` is removed from `src/services/models.py`; no code path
  assumes a fixed router-model id.
- `src/api/chat.py` routes a chat request to the router iff the router is
  configured AND `is_router_model(request.model)` — any ready model. A
  model not in the ready set is no longer 422 pre-stream: the router
  branch simply does not match and the request follows the internal
  (local) path exactly as before the router existed.
- 404 race: when a router-routed stream errors without a message, the
  handler re-probes; if the model has left the ready set it emits the
  exact not-ready message — `Model {id} is not ready in Vortex. Pick a
  local model or retry once it is loaded.` — instead of the generic
  fallback (AC-179). A stream error while the model is still ready keeps
  the generic fallback (AC-180). The re-probe is the discriminator.
- No change to `src/services/llm.py`: its message-less `("error",)`
  swallow is the seam the recut hooks.
- Transport seams unchanged: `router_chat_endpoint()` (base +
  `/v1/chat/completions`) and `_router_probe()` (parse `.data[].id`)
  already match v26 — the recut must not churn them.
- Vortex's management surface (catalog, model lifecycle, operations
  endpoints) stays untouched by testchat; it is T9's "Manage models in
  Vortex" link.

## Changed acceptance criteria

- AC-175 (new, supersedes AC-170): the full ready set — every id the
  router lists, probe order, deduplicated, source `router` — appears in
  `GET /api/v1/models`.
- AC-176 (new, supersedes AC-171): probe failure or an empty ready set
  omits all router models from `GET /api/v1/models`; router models are
  never in `GET /api/v1/models/catalog`.
- AC-177 (new, supersedes AC-172): chat naming ANY ready router model
  streams from `{VORTEX_URL}/v1/chat/completions` with the id passed
  through unchanged.
- AC-178 (new, supersedes AC-173): a model not in the ready set is NOT
  rejected pre-stream — the request falls through to the local path.
- AC-179 (new): a router-routed stream error after the model left the
  ready set surfaces the exact not-ready message with a local fallback
  offer, as a 200 SSE error event.
- AC-180 (new): a router-routed stream error while the model is still
  ready keeps the generic fallback message.
- AC-181 (new): `ROUTER_MODEL_ID` is retired; no fixed router model id
  exists in `src/services/models.py`.

## Superseded acceptance criteria

- AC-170 (the single router model listed when the router lists it) —
  superseded by AC-175 (the full ready set is listed).
- AC-171 (the router model omitted when the probe fails or omits it) —
  superseded by AC-176 (all router models omitted on probe failure /
  empty set; the catalog exclusion carries forward).
- AC-172 (the router model's chat streams from the router endpoint) —
  superseded by AC-177 (any ready model's chat does).
- AC-173 (router-model chat not listed at that moment is 422 pre-stream)
  — superseded by AC-178 (not-ready falls through to the local path) and
  AC-179 (the mid-flight 404 race surfaces a not-ready notice, never a
  server error).
- AC-174 (VORTEX_URL unset: no router model, no probe) stands unchanged.

## Changed files

- `src/services/models.py` (UPDATED): `router_models()` returns the full
  ready set; `is_router_model()` is dynamic membership; `ROUTER_MODEL_ID`
  removed.
- `src/api/chat.py` (UPDATED): the router branch routes any ready model;
  not-ready models fall through to the local path; the message-less
  stream-error branch re-probes and emits the AC-179 not-ready message
  when the model has left the ready set.
- `src/api/models.py` (no edit — acceptance-only): its
  `GET /api/v1/models` and `GET /api/v1/models/catalog` routes are the
  observation surface for AC-175/AC-176; they already serve whatever
  `list_models()` / `list_model_catalog()` return.
- `tests/test_router_route.py` (UPDATED: full recut of the v107 oracle —
  eight tests updated in place, two v107 names retired
  (`test_chat_router_model_not_listed_is_422`,
  `test_chat_router_model_router_down_is_422`), five new tests pinned in
  the mapping below).
- `scripts/.approved/contracts.json` — staged delta: `erd_version` 115,
  `files` restated (the full oracle-mapping inventory; every member
  explained by `changed_files` or `no_edit_files`), `changed_files`
  declared, `no_edit_files` restated with `src/api/models.py` added as
  acceptance-only, `test_mapping` restated (the two retired v107 router
  pins dropped; the new tests are pinned in this delta's mapping section
  until they are frozen node-ids).

## Test-to-file mapping

* `tests/test_router_route.py::test_is_router_model_true_for_any_ready_id`
  -> `src/services/models.py`
* `tests/test_router_route.py::test_is_router_model_false_when_not_listed_or_down`
  -> `src/services/models.py`
* `tests/test_router_route.py::test_router_model_id_constant_retired`
  -> `src/services/models.py`
* `tests/test_router_route.py::test_chat_router_model_not_listed_falls_through_to_local_path`
  -> `src/api/chat.py`
* `tests/test_router_route.py::test_chat_router_model_router_down_falls_through_to_local_path`
  -> `src/api/chat.py`
* `tests/test_router_route.py::test_chat_router_404_race_surfaces_not_ready_message`
  -> `src/api/chat.py`
* `tests/test_router_route.py::test_chat_router_error_while_still_ready_is_generic`
  -> `src/api/chat.py`
