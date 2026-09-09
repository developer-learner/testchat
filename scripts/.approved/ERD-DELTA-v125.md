# ERD-DELTA v125 — complete the T9 frontend integration

## Design

Reconcile the stale ui:model-select contract (which still prescribed catalog
merging) with the already-approved T9 ready-only design. Rebuild the two failed
frontend files. Existing six T9 tests and their owner pins remain byte-identical.
The existing app consumes Catalog.fetchModels as a promise and gates Send on
option.dataset.loaded; both interfaces must remain functional. Source state
comes from the selected optgroup, avoiding a separate stale model cache.

## Changed acceptance criteria

AC-184, AC-186, AC-187 and AC-188 are unchanged in product scope. Their UI
contracts now explicitly describe the approved grouped ready-only behavior and
its initialization/refresh integration. No new acceptance criteria or tests.

## Superseded acceptance criteria

None beyond the AC retirements already frozen in v123.

## Changed files

- `src/static/catalog.js` — ready-only groups, ready selection and manage state.
- `src/static/app.js` — source indicator initialization and promise integration.

## Coder briefs (verbatim)

### T1 — src/static/catalog.js

Edit only src/static/catalog.js. Replace the old catalog/lifecycle module with
the T9 ready-only grouped picker. Preserve the localStorage thread-model helpers
and the public exports fetchModels, refreshModels, storedThreadModel and
storeThreadModel. Preserve lazy pollStatus/appendBubble delegation to window.App.

fetchModels RETURNS the fetch promise for /api/v1/models. Parse data.models and
data.router (default configured:false, reachable:false), populate the picker,
then resolve to the models array. On error show a blank-valued failure option,
disable the manage link, poll status, and resolve to [] to avoid an unhandled
rejection. refreshModels returns fetchModels(). Fetch only /api/v1/models.

populateModelOptions(models, router) captures the old selection, or stored active
thread model, or active thread.model, BEFORE clearing the select. Partition by
source === 'router'. Create real optgroups labelled 'Vortex · shared · primary'
first and 'Local · this machine · fallback' second. Keep a configured Vortex
group visible even with zero models; disable it when router.reachable is false.
Local group stays enabled. Each option uses model.id as value, green glyph plus
id as text, and dataset.loaded='true'. Preserve an existing selection only if
its group is enabled; otherwise choose the first enabled option. If none is
available use a blank-valued 'No models available' placeholder. Synchronize the
active thread.model to the chosen value and toggle select-empty. After rebuilding,
pollStatus() so the status/source/Send state updates immediately.

Set manage-in-vortex aria-disabled='true' when unreachable and remove that
attribute when reachable. Its click handler prevents navigation while disabled
(aria-disabled alone does not prevent navigation).

The model-select change listener records thread.model, calls storeThreadModel
and pollStatus; it never opens a modal. Remove all local lifecycle controls,
their listeners/timers, scriptModelLoaded references, and catalog endpoint calls.
Self-verify: real optgroups, enabled fallback selection, promise return,
dataset.loaded, reachability-aware manage action, no null Eject listener.

### T2 — src/static/app.js

Edit only src/static/app.js. Preserve chat streaming, thread hydration, history,
websearch, and routing. Keep existing ready-only send behavior.

Replace updateSourceIndicator's model-cache lookup with selected option's parent
optgroup: enabled group whose label contains 'Vortex' means 'via Vortex'; all
other cases mean 'via local'. Remove modelsCache and routerReachable declarations
and assignments. The old cache is both stale and read before initialization by
the first pollStatus call; the DOM-based helper must be safe at that first call.
Keep the helper called by pollStatus and the model-select change listener.
At initialization replace Catalog.fetchModels().then callback with a callback
that calls pollStatus after the returned promise resolves. Catalog now returns
a promise and sets dataset.loaded on ready options. Thread switches already
invoke pollStatus via the public App interface, so source follows thread changes.
Remove any remaining local load/unload/Eject UI flow if present. Self-verify:
source reads the enabled optgroup, first pollStatus is safe, Send remains enabled
for a selected ready option, models load without a synchronous exception.

## Task DAG

- src/static/catalog.js precedes src/static/app.js.
- Other files retain their already-built behavior; no new work is requested.

## Test-to-file mapping

The six T9 tests retain their frozen v124 owner mappings. The grouped and offline
tests belong to catalog.js; source-indicator test belongs to app.js. Backend
and manage-link markup tests remain acceptance evidence for their existing files.
