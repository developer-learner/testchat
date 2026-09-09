# ERD-DELTA v123 — Vortex cutover (T9): grouped ready-only picker, manage link, source indicator, fallback

Freeze context: the CEO-approved T9 design (`tasks/T9-cutover-design.md`,
2026-09-01) makes Vortex the primary model source and the picker ready-only,
while KEEPING the local path (LM Studio + script models) as a labelled
fallback. Model lifecycle (load/unload/catalog/RAM) lives in Vortex, never in
Testchat, so the local Eject/load/unload UI is removed. Phase 3 already shipped
the router seams (`is_router_configured`, `router_chat_endpoint`,
`router_models`, `is_router_model`, `VORTEX_URL`); this milestone builds the
cutover UX on top of them.

The normal deployment points `VORTEX_URL` at the router
(`http://127.0.0.1:9000`) via `.env` — NOT a code default: the frozen suite
boots the app under test without `VORTEX_URL`, so a hardcoded router default
would make `list_models()` probe a real `:9000` and break suite hermeticity.
Rollback is an explicit env change; it restores no lifecycle UI.

## Design (by file / task)

- **T1 `src/services/models.py`** — add `router_status() -> dict` returning
  `{"configured": bool, "reachable": bool}`: `configured` is
  `is_router_configured()` (VORTEX_URL set); `reachable` is
  `_router_probe() is not None` (the probe returns None only when the router is
  unset or unreachable, `[]` when reachable-but-empty). No other behavior
  changes. This is the signal the UI needs to tell "Vortex down" from "Vortex
  up but no models loaded."
- **T2 `src/api/models.py`** — the `GET /api/v1/models` response gains a
  `router` object `{"configured": bool, "reachable": bool}` from
  `router_status()`, alongside the existing `models` list. `ModelsListResponse`
  grows a `router: RouterStatus` field. Route path and the `models` shape are
  unchanged (additive).
- **T3 `src/static/catalog.js`** — the dropdown becomes a **ready-only, grouped
  picker** built from `/api/v1/models` alone (no `/api/v1/models/catalog`
  fetch, no load/unload/Eject wiring):
  - Two `<optgroup>`s: label `Vortex · shared · primary` holds models with
    `source === "router"`; label `Local · this machine · fallback` holds every
    other (local) model. A group with no members is omitted.
  - A **"Manage models in Vortex ↗"** control (testid `manage-in-vortex`) sits
    with the Vortex group; clicking it opens `http://127.0.0.1:9000/` in a new
    tab.
  - **Fallback:** when `router.reachable` is false, the Vortex optgroup and the
    manage control are disabled; local models stay selectable. When
    `router.configured` is false, treat as local-only (no Vortex group/link).
    A response with no `router` field (older stubs) is treated as
    not-configured — local-only — so carried tests keep working.
  - Selecting any listed model performs NO load confirmation (all listed models
    are ready); it records the thread's model and polls status.
- **T4 `src/static/index.html`** — add the `manage-in-vortex` anchor and an
  `active-model-source` element in the status strip; REMOVE the Eject button
  (`#eject-model-btn`) and the `#load-confirm-modal` and `#unload-confirm-modal`
  blocks (lifecycle lives in Vortex).
- **T5 `src/static/app.js`** — set the `active-model-source` indicator to
  `via Vortex` when the active model's source is `router` (and the router is
  reachable), else `via local`; REMOVE the load-on-send flow (the
  `#load-confirm-modal` path that POSTs `/api/v1/script-models/{id}/load` before
  sending) and the Eject-button wiring. Chat routing is unchanged (Phase 3:
  router models route to `router_chat_endpoint`, local to the internal path).

Backend `/script-models/*` load/unload routes are NOT removed — they remain as
the local fallback supply and the documented rollback surface.

## Changed acceptance criteria

- **AC-183 (new):** `GET /api/v1/models` returns, alongside `models`, a
  `router` object with boolean `configured` and `reachable`, such that a client
  can distinguish an unreachable router from a reachable-but-empty one.
- **AC-184 (new):** the model picker is ready-only and grouped — a
  `Vortex · shared · primary` optgroup lists `source == "router"` models and a
  `Local · this machine · fallback` optgroup lists the rest; the full unloaded
  catalog is never listed, such that only chat-ready models are selectable.
- **AC-185 (new):** a `manage-in-vortex` control labelled "Manage models in
  Vortex ↗" targets `http://127.0.0.1:9000/` and opens in a new browser tab,
  such that model management is reached in Vortex, not Testchat.
- **AC-186 (new):** when `router.reachable` is false, the Vortex optgroup and
  the `manage-in-vortex` control are disabled while local models stay
  selectable, such that Testchat keeps working on the local fallback when
  Vortex is down.
- **AC-187 (new):** the `active-model-source` indicator reads `via Vortex` when
  the active model is a reachable router model and `via local` otherwise, such
  that the active model's source is visible in the status strip.
- **AC-188 (new; supersedes AC-31, AC-132, AC-167):** the normal UI exposes no
  local model-lifecycle action — the Eject button and the load-confirm and
  unload-confirm modals are absent from the page — such that Vortex owns model
  lifecycle; selecting a ready model performs no load confirmation and simply
  becomes the thread's model.

## Superseded acceptance criteria

- **AC-31** (selection survives a models refresh): retired — its Eject-driven
  trigger is removed; selector behavior is covered by AC-133 and AC-184.
- **AC-132** (the unloaded-model load prompt): retired — there is no
  load-confirm flow; the picker lists only ready models.
- **AC-167** (script-catalog dropdown dedup): retired — the catalog is no
  longer fetched or merged; the picker is built from `/api/v1/models` alone.

## Changed files

- `src/services/models.py` — add `router_status()`.
- `src/api/models.py` — add `router` to the `/api/v1/models` response.
- `src/static/catalog.js` — grouped ready-only picker + manage link + fallback;
  remove catalog fetch and lifecycle wiring.
- `src/static/index.html` — add manage link + source indicator; remove Eject
  button and the two lifecycle modals.
- `src/static/app.js` — source indicator; remove the load-on-send flow.

(Test files re-staged in the same delta: `tests/test_vortex_cutover.py` added;
the retired lifecycle tests removed from `tests/test_ui.py` and
`tests/test_ui_catalog.py`; `tests/conftest.py` cleaned. `.env.example` and
docs are updated in the conductor lane, outside the coder tasks.)

## Coder briefs (verbatim)

### T1 — src/services/models.py

Edit only `src/services/models.py`. Add one public function
`router_status() -> dict[str, bool]` that returns
`{"configured": is_router_configured(), "reachable": _router_probe() is not None}`.
Do not change any existing function, import, or constant. `is_router_configured`
and `_router_probe` already exist in this module. Self-verify: `router_status`
is defined at module scope and calls the two existing helpers; nothing else
changed.

### T2 — src/api/models.py

Edit only `src/api/models.py`. Import `router_status` from
`src.services.models`. Add a Pydantic model
`class RouterStatus(BaseModel): configured: bool; reachable: bool`. Add a field
`router: RouterStatus` to `ModelsListResponse`. In `get_models()`, build the
response as
`ModelsListResponse(models=[ModelInfo(**m) for m in list_models()], router=RouterStatus(**router_status()))`.
Do not change the route path, the `ModelInfo` shape, or any other route. Self-
verify: `GET /api/v1/models` still returns `models`, and now also `router` with
`configured` and `reachable` booleans.

### T3 — src/static/catalog.js

Edit only `src/static/catalog.js`. Rebuild the model-dropdown module as a
ready-only, grouped picker with no load/unload/Eject behavior and no
script-model catalog fetch.

KEEP: the `THREAD_MODEL_STORE_KEY` store and its helpers
(`readThreadModelStore`, `storeThreadModel`, `storedThreadModel`); the
`model-select` handle; the `appendBubble`/`pollStatus` delegators;
`refreshModels` (calls `fetchModels`); the returned object exposing
`fetchModels`, `refreshModels`, `storedThreadModel`, `storeThreadModel`.

REMOVE: every `getElementById` handle and listener for `eject-model-btn`,
`load-confirm-modal`, `load-confirm`, `load-cancel`, `load-confirm-text`,
`unload-confirm-modal`, `unload-confirm`, `unload-cancel`, `unload-confirm-text`;
the `TC.scriptModelLoaded` computation; the selector focus/blur/mousedown
Eject-reveal listeners; and, in the `change` listener, the entire unloaded-pick
load-confirm branch — a change now only records the thread's model
(`previousModelValue`, `thread.model`, `storeThreadModel`) and calls
`pollStatus()`.

CHANGE `fetchModels`: request ONLY `/api/v1/models`. Read `data.models` (each
has `id` and `source`) and `data.router` (`{configured, reachable}`; if absent,
treat as `{configured:false, reachable:false}`). Build the `<select>` with two
`<optgroup>`s:
- `Vortex · shared · primary`: models whose `source === "router"`. If
  `data.router.reachable` is false, set this optgroup's `disabled = true`.
- `Local · this machine · fallback`: all other models, always selectable.
Omit an optgroup that has no models. Render each option as `🟢 <id>` (all listed
models are ready). Preserve the previous/stored selection restore and the
`select-empty` toggle. On fetch failure, set
`modelSelect.innerHTML = '<option value="">Failed to load models</option>'`.

Add the manage control: get `document.getElementById('manage-in-vortex')`; set
its `disabled`/`hidden` to reflect `!data.router.reachable` (disabled when the
router is unreachable). Its click opens `http://127.0.0.1:9000/` in a new tab
(`window.open('http://127.0.0.1:9000/', '_blank')`); if it is an anchor with a
correct `href`/`target`, no click handler is needed.

Do not change any other file. Self-verify: no reference to `eject`,
`load-confirm`, `unload`, or `/models/catalog` remains; the dropdown has two
labelled optgroups; the manage control reflects `router.reachable`.

### T4 — src/static/index.html

Edit only `src/static/index.html`. Two additions and three removals, nothing
else:
ADD (in the status strip, near `#status-model`): an element
`<span id="active-model-source" data-testid="active-model-source"></span>` for
the source indicator; and an anchor
`<a id="manage-in-vortex" data-testid="manage-in-vortex" href="http://127.0.0.1:9000/" target="_blank" rel="noopener">Manage models in Vortex ↗</a>`
placed with the model selector.
REMOVE: the Eject button (`id="eject-model-btn"`); the entire
`#load-confirm-modal` overlay block; the entire `#unload-confirm-modal` overlay
block. Leave every other element unchanged (settings modal, delete-confirm
modal, `model-select`, status strip). Self-verify: the file contains
`active-model-source`, `manage-in-vortex`, `model-select`, `delete-confirm-modal`;
and no `eject-model-btn`, `load-confirm-modal`, or `unload-confirm-modal`.

### T5 — src/static/app.js

Edit only `src/static/app.js`. Two changes:
1. Source indicator: get `document.getElementById('active-model-source')`. When
   the active model is set, read the current models list (or the selected
   option's group) to determine source; set the element's text to `via Vortex`
   when the active model's `source === "router"` and the router is reachable,
   else `via local`. Update it wherever the active model or model list changes
   (initial load, model switch, and after `fetchModels`).
2. REMOVE the load-on-send flow: delete the branch that, on send with an
   unloaded selected model, opens `#load-confirm-modal` and POSTs
   `/api/v1/script-models/{id}/load` before resubmitting; delete the
   `eject-model-btn`, `load-confirm-modal`, `load-confirm`, `load-cancel`
   handles and their listeners. Sending with a ready model proceeds directly
   to chat (unchanged). Do not change chat streaming, routing, websearch, or
   any other file. Self-verify: no `script-models/.../load`, `load-confirm`, or
   `eject` reference remains in app.js; the source indicator is set on model
   change.

## Task DAG

- T1 = `src/services/models.py` (no deps).
- T2 = `src/api/models.py`, depends_on T1.
- T3 = `src/static/catalog.js`, depends_on T2.
- T4 = `src/static/index.html` (no deps).
- T5 = `src/static/app.js`, depends_on T2 and T4.

## Test-to-file mapping

* `tests/test_vortex_cutover.py::test_router_status_reflects_configured_and_reachable`
  -> `src/services/models.py`
* `tests/test_vortex_cutover.py::test_get_models_includes_router_object`
  -> `src/api/models.py`
* `tests/test_vortex_cutover.py::test_picker_is_ready_only_and_grouped`
  -> `src/static/catalog.js`
* `tests/test_vortex_cutover.py::test_vortex_group_and_manage_disabled_when_unreachable`
  -> `src/static/catalog.js`
* `tests/test_vortex_cutover.py::test_manage_in_vortex_link_targets_router`
  -> `src/static/index.html`
* `tests/test_vortex_cutover.py::test_active_model_source_indicator`
  -> `src/static/app.js`
