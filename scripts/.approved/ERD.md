ERD — testchat M27: DeepSeek V4 Flash (erd_version 50)

What changes v49 -> v50

Ratify shape (D-63), same pattern as M26/v49. The tree already carries
every M27 code change (five modified files listed below) from a prior
CEO session; the pipeline run here is a coder no-op. The M27 delta is
spec-only: contracts pick up the two new routes, two new UI testids,
two new response schemas, and the extended ModelInfo.source enum. New
tests pin the behavior. Build inventory is UNCHANGED from v49 (same
10 files).

Behavior newly locked

- AC-94 / AC-95 script-model load/unload — `src/services/models.py`
  gains a `SCRIPT_MODELS` registry and generic
  `load_script_model` / `unload_script_model` / `is_script_model_loaded`.
  Nemotron is one entry, `deepseek-v4-flash` is the second. Backing
  server: `/Users/arc.elixir/dev/ds4/run-server.sh` at
  http://127.0.0.1:8000. Pinned by new tests
  `test_models_service.py::test_registry_contains_expected_script_models`,
  `test_load_deepseek_spawns_and_confirms_ready`,
  `test_load_deepseek_timeout_clears_process_and_errors`, and
  `test_load_deepseek_unloads_running_nemotron_first` /
  `test_load_nemotron_unloads_running_deepseek_first`
  (mutual exclusion, both directions).
- AC-96 mutual exclusion — `_unload_other_script_models` runs before
  spawning. Pinned by the mutual-exclusion test above.
- AC-97 chat routing — `src/api/chat.py` looks the requested model
  up in `get_script_model` and routes via `is_script_model_loaded`
  instead of the old name-hardcoded nemotron check. Pinned by
  `test_chat_model_routing.py::test_chat_routes_to_deepseek_and_passes_model`
  and `::test_chat_deepseek_selected_but_not_loaded_is_422`.
- AC-98 model listing — `list_models()` iterates `SCRIPT_MODELS` and
  emits `{"id": model_id, "source": model_id}` per ready model. The
  `ModelInfo.source` enum expands to include `"deepseek-v4-flash"`.
- AC-99 generic endpoints — `POST /api/v1/script-models/{model_id}/load`
  and `.../unload` in `src/api/models.py`, dispatching through the
  registry. The nemotron aliases stay, wired to the same handlers.
  Pinned by new tests in `test_models_api.py` covering both endpoint
  shapes (404 on unknown id, 200 on load, 503 on timeout, alias parity).

Files where the DeepSeek code lives but which are NOT added to the
inventory

- `src/services/models.py` — the registry + script-model machinery.
  Not in inventory, same treatment as `src/main.py` in M25/M26 (an
  entry-point / infrastructure file the ratify pins by test rather
  than by task). Adding it to the inventory would turn every future
  script-model tweak into a coder-task freeze cycle, which is
  disproportionate for a file changing on the order of once per
  quarter. Behavior is locked by `tests/test_models_service.py` (17
  tests) and `tests/test_models_api.py` (14 tests) both importing the
  module and exercising its surface.
- `src/api/models.py` — the FastAPI route module. Same treatment for
  the same reason: pinned by tests, not by inventory.

File inventory (M27 build) — UNCHANGED from v49

Same 10 files as v49. Same no_edit_files as v49 (markdown.js, rain.js,
style.css). No tasks add new inventory members.

DAG: EMPTY-EQUIVALENT. The EM MUST emit a plan matching the v49 shape
(10 tasks, one per inventory file, each brief saying "no edits — carry
forward as-is", each mapped to the same test node-ids plus any new
node-ids that touch that file). The two new test files map to
existing tasks:

- `tests/test_chat_model_routing.py::test_chat_routes_to_deepseek_and_passes_model`
  → task T3 (`src/api/chat.py`)
- `tests/test_chat_model_routing.py::test_chat_deepseek_selected_but_not_loaded_is_422`
  → task T3
- `tests/test_models_api.py::test_*` (14 new tests) → carried-forward
  regression (`src/api/models.py` is not in inventory; D-57 auto-carry
  handles them at the shell)
- `tests/test_models_service.py::test_*` (17 new tests) → carried-forward
  regression (`src/services/models.py` is not in inventory; D-57 auto-carry)
- One new `test_ui.py` node? — NONE. UI tests unchanged in this
  freeze. The two new buttons are click-tested only via the backend
  (script-model endpoint tests). Adding a UI regression for the
  buttons is queued as an optional M28 tightening if a UI bug ever
  slips through.

Contract ids per task: unchanged from v49 (empty for the ratified
tasks, since no task claims a contract in ratify mode).

Oracle Mapping — carried-forward regression rides D-57 auto-carry for
the on-src/services/models.py and on-src/api/models.py tests; the
two on-src/api/chat.py tests map to T3 as noted above.

Smoke checks strengthened (M27)

- `src/api/chat.py`: also greps for `get_script_model` (the routing
  now goes through the registry, not a hard-coded nemotron name).
- `src/static/index.html`: also greps for
  `data-testid="load-deepseek"` (the new button is a smoke-visible
  presence check).
- `src/static/app.js`: also greps for `loadDeepseekBtn` and
  `deepseek-v4-flash` (the new event listeners and endpoint literals).

Rollback / risk

- Rolling back M27 means removing DeepSeek entries from
  `SCRIPT_MODELS`, removing the two UI buttons, and reverting chat.py
  to name-hardcoded nemotron routing. The nemotron aliases keep
  backwards compat for anything wired to `/api/v1/nemotron/load|unload`.
- Risk: the DeepSeek server binary (`/Users/arc.elixir/dev/ds4/run-server.sh`)
  is a hard-coded absolute path — portable-only to the CEO's box.
  Same shape as nemotron's `~/nemotron-vmlx.py`; this is deliberate for
  the local-first design and revisited only if the deployment target
  changes.

M28 — model-control UI consolidation (dropdown + eject)

Problem: M27 shipped the DeepSeek controls by copying the nemotron
pattern, leaving four per-model load/unload buttons in the top bar.
The pattern grows two buttons per registered script model; the
registry (M27) already made per-model buttons redundant.

Design:

- The model-select dropdown becomes the single load control. It lists
  loaded LM Studio models (from GET /api/v1/models, contract
  unchanged) PLUS every script-model registry entry regardless of
  load state, from a NEW endpoint:

  GET /api/v1/models/catalog ->
    {"models": [{"id", "source", "loaded": bool}, ...]}

  (script models only; LM Studio discovery stays on /api/v1/models).
  Options carry the load state in the label ("(loaded)" vs
  "- click to load") and data-model-id / data-loaded attributes.

- Selecting an unloaded script model POSTs
  /api/v1/script-models/{id}/load (dropdown disabled while the
  ready-poll runs; failures surface via the chat error bubble).
  Mutual exclusion is backend-owned (M27) — the UI never reasons
  about which model to evict.

- A single eject button (testid eject-model-btn, replaces the four
  per-model buttons and their testids load-nemotron/unload-nemotron/
  load-deepseek/unload-deepseek) queries the catalog, finds the
  loaded script model, POSTs its /unload. No-op when none loaded.

Oracle Mapping

- AC-31 (test_model_selection_survives_models_refresh) re-anchored:
  the refresh trigger is now the eject button, with the catalog and
  unload endpoints route-stubbed in-page (the conftest stub keeps
  serving /api/v1/models untouched).

Smoke checks (replacing the M27 button greps)

- `src/static/index.html`: greps `data-testid="eject-model-btn"`.
- `src/static/app.js`: greps `ejectModelBtn` and `models/catalog`.

Rollback / risk

- Rollback = restore the four buttons and their testids, drop the
  catalog route. The /api/v1/models contract is untouched either way,
  so chat routing and model listing carry zero risk from M28.
- Risk: the dropdown now triggers a heavyweight action (a 100GB-class
  server launch) on select. Accepted deliberately (speed-first);
  the visible loading state is the mitigation.

M28a — wordless model states + confirm gates (amends M28, pre-implementation)

CEO corrections to the M28 UI before any code lands. Model state is
communicated by glyphs, not words (native selects render color emoji
but not CSS), and both heavyweight actions get a confirmation gate.

Dropdown option labels:

- "○ {id}"        — unloaded; selecting it opens load-confirm-modal
- "○/🟢 blinking"  — loading: after confirm, the selected option's
                    glyph alternates ○↔🟢 (~600ms) while the ready-
                    poll runs; dropdown disabled. Settles to solid 🟢
                    on ready, reverts to ○ on failure (the existing
                    chat error bubble carries the reason).
- "🟢 {id}"        — loaded (resident in RAM)
- "✓ 🟢 {id}"      — loaded AND the model the current chat thread is
                    using (a model can be 🟢 without ✓)

Confirm gates (both reuse the settings-modal overlay pattern):

- load-confirm-modal: opens on selecting an unloaded script model;
  shows the model name and the live RAM line from /api/v1/status
  (ram_used/ram_total/loadable_gb). Confirm (load-confirm) POSTs the
  load; cancel (load-cancel) reverts the dropdown selection, sends
  nothing. Rationale: a stray dropdown click launching a 100GB-class
  server can push the machine into memory pressure; loading must be
  a deliberate two-step action.
- unload-confirm-modal: opened by eject-model-btn, names the loaded
  model. Confirm (unload-confirm) POSTs the unload; cancel
  (unload-cancel) sends nothing.

Eject visibility: eject-model-btn is right-aligned beside the
dropdown and hidden by default; it is revealed while the dropdown
has focus (closest native-select approximation of "visible while
the model menu is open") and hides on blur.

Oracle Mapping: AC-31 gains one step — after clicking
eject-model-btn it clicks unload-confirm (the eject path now runs
through the confirm gate). The eject button remains reachable via
testid regardless of the focus-reveal styling. The load-confirm
elements enter the locked surface for future oracles.

M28b — inventory correction (amends M28, spec defect)

v51 froze the GET /api/v1/models/catalog route but never added its
implementing files to the ERD inventory (contracts.files), making the
milestone unimplementable: validate-plan.py requires an exact
bijection between plan tasks and the inventory, so no valid plan
could contain a task that builds the catalog endpoint. Caught at the
plan gate after two EM models failed against an impossible spec.

Correction: src/services/models.py (gains list_model_catalog(),
returning every SCRIPT_MODELS entry as {id, source, loaded}) and
src/api/models.py (gains the catalog route delegating to it) join
contracts.files, each with a smoke check. Their existing frozen tests
(tests/test_models_service.py, tests/test_models_api.py) map to these
tasks per the standard oracle projection.
