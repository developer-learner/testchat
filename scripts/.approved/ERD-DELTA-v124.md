# ERD-DELTA v124 — pin the T9 browser tests to their owner files; rebuild the grouped picker

Freeze context: v123 (T9) froze the Vortex-cutover tests and built the code,
but its browser tests were left unpinned in `contracts.test_mapping`, so D-64
moved them all onto the DAG's final task and `src/static/catalog.js` /
`src/static/app.js` were accepted without ever running their UI tests — and
independent verification then showed the grouped picker and the source
indicator are broken (`catalog.js` renders no options). This delta carries NO
new behavior and NO new AC: it (1) pins each T9 test to its behavioral-owner
file in `contracts.test_mapping` so a failing UI test retries the RIGHT file,
and (2) re-issues `catalog.js` and `app.js` for a correct rebuild against those
now-mapped tests. AC-183..AC-188 (v123) are unchanged.

## Design

- **`src/static/catalog.js`** — rebuild the model picker as a ready-only,
  two-group dropdown; the manage control reflects router reachability; and the
  script-model catalog fetch and the local lifecycle wiring are gone. The v123
  build produced a dropdown with no options; the brief below spells out the
  exact DOM construction.
- **`src/static/app.js`** — the `active-model-source` indicator reads
  `via Vortex` for a reachable router model and `via local` otherwise, and the
  local load-on-send flow is removed.
- No other file changes; the backend (`services/models.py`, `api/models.py`)
  and `index.html` already pass their pinned tests and are acceptance-only.

## Changed acceptance criteria

None. This delta re-pins existing tests and rebuilds two files against them.

## Superseded acceptance criteria

None. AC-183 through AC-188 (v123) are unchanged; this delta only pins their
tests to owner files and rebuilds the two files that failed them.

## Changed files

- `src/static/catalog.js` — rebuild the grouped ready-only picker + manage
  control; no catalog fetch, no lifecycle wiring.
- `src/static/app.js` — source indicator; remove the load-on-send flow.

## Coder briefs (verbatim)

### T1 — src/static/catalog.js

Edit only `src/static/catalog.js`. Rebuild the model-dropdown module. Keep the
`THREAD_MODEL_STORE_KEY` localStorage map and its helpers
(`readThreadModelStore`, `storeThreadModel`, `storedThreadModel`), the
`var modelSelect = document.getElementById('model-select');` handle, the
`appendBubble` and `pollStatus` lazy delegators, `refreshModels` (which calls
`fetchModels`), and the returned object exposing `fetchModels`,
`refreshModels`, `storedThreadModel`, `storeThreadModel`.

Remove every reference to `eject-model-btn`, `load-confirm-modal`,
`load-confirm`, `load-cancel`, `load-confirm-text`, `unload-confirm-modal`,
`unload-confirm`, `unload-cancel`, `unload-confirm-text`, `TC.scriptModelLoaded`,
and the `/api/v1/models/catalog` fetch; there must be no load, unload, or Eject
behavior left.

Replace `fetchModels` with exactly this shape:

```
function fetchModels() {
  fetch('/api/v1/models')
    .then(function (r) { if (!r.ok) throw new Error('Failed to fetch models'); return r.json(); })
    .then(function (data) {
      var models = (data && data.models) || [];
      var router = (data && data.router) || { configured: false, reachable: false };
      populateModelOptions(models, router);
    })
    .catch(function () {
      modelSelect.innerHTML = '<option value="">Failed to load models</option>';
    });
}
```

Replace `populateModelOptions` so it takes `(models, router)` and builds two
`<optgroup>`s. Preserve the previously-selected value across a rebuild by
reading `modelSelect.value` (or the stored thread model) BEFORE clearing, and
re-selecting it after. Concretely:

```
function populateModelOptions(models, router) {
  var previous = modelSelect.value || storedThreadModel(TC.activeThreadId) || '';
  modelSelect.innerHTML = '';

  var vortex = [];
  var local = [];
  for (var i = 0; i < models.length; i++) {
    if (models[i].source === 'router') { vortex.push(models[i]); }
    else { local.push(models[i]); }
  }

  function addGroup(label, list, disabled) {
    if (!list.length) return;
    var og = document.createElement('optgroup');
    og.label = label;
    if (disabled) og.disabled = true;
    for (var j = 0; j < list.length; j++) {
      var o = document.createElement('option');
      o.value = list[j].id;
      o.textContent = '🟢 ' + list[j].id;
      og.appendChild(o);
    }
    modelSelect.appendChild(og);
  }

  addGroup('Vortex · shared · primary', vortex, !router.reachable);
  addGroup('Local · this machine · fallback', local, false);

  if (!modelSelect.options.length) {
    modelSelect.innerHTML = '<option value="">No models available</option>';
  } else if (previous) {
    modelSelect.value = previous;
  }
  modelSelect.classList.toggle('select-empty', !modelSelect.value);

  var manage = document.getElementById('manage-in-vortex');
  if (manage) {
    if (router.reachable) { manage.removeAttribute('aria-disabled'); }
    else { manage.setAttribute('aria-disabled', 'true'); }
  }
}
```

The `change` listener must NOT open any modal. For every pick it records the
thread's model and polls status:

```
modelSelect.addEventListener('change', function () {
  modelSelect.classList.toggle('select-empty', !modelSelect.value);
  var thread = TC.threads.find(function (t) { return t.id === TC.activeThreadId; });
  if (thread) thread.model = modelSelect.value;
  storeThreadModel(TC.activeThreadId, modelSelect.value);
  pollStatus();
});
```

Do not change any other file. Self-verify: the file contains
`document.createElement('optgroup')`, the two group labels `Vortex` and
`Local`, `manage-in-vortex`, and `data.router`; and contains no `eject`,
`load-confirm`, `unload`, or `/models/catalog`.

### T2 — src/static/app.js

Edit only `src/static/app.js`. Two changes.

(1) Source indicator: after the model list is available and whenever the active
model changes, set the `active-model-source` element's text. Add a helper and
call it after `fetchModels` completes and in the model-select `change` handler:

```
function updateActiveModelSource() {
  var el = document.getElementById('active-model-source');
  if (!el) return;
  var sel = document.getElementById('model-select');
  var opt = sel && sel.options[sel.selectedIndex];
  var group = opt && opt.parentNode;                       // <optgroup>
  var isVortex = group && /Vortex/.test(group.label || '');
  el.textContent = isVortex ? 'via Vortex' : 'via local';
}
```

Call `updateActiveModelSource()` on page init after models load and inside the
`model-select` `change` listener. (The active option's parent `<optgroup>`
label carries the source, so no extra request is needed.)

(2) Remove the load-on-send flow: delete the branch that, on send with an
unloaded selected model, opens `#load-confirm-modal` and POSTs
`/api/v1/script-models/{id}/load` before resubmitting, and delete the
`eject-model-btn`, `load-confirm-modal`, `load-confirm`, `load-cancel` handles
and their listeners. Sending with a ready model proceeds straight to chat,
unchanged. Do not change chat streaming, routing, websearch, or any other file.
Self-verify: no `script-models/.../load`, `load-confirm`, or `eject` reference
remains; `active-model-source` is set on init and on model change.

## Task DAG

- T1 = `src/static/catalog.js` (no deps).
- T2 = `src/static/app.js`, depends_on T1 (the source indicator reads the
  optgroup structure catalog.js builds).

## Test-to-file mapping

* `tests/test_vortex_cutover.py::test_picker_is_ready_only_and_grouped`
  -> `src/static/catalog.js`
* `tests/test_vortex_cutover.py::test_vortex_group_and_manage_disabled_when_unreachable`
  -> `src/static/catalog.js`
* `tests/test_vortex_cutover.py::test_active_model_source_indicator`
  -> `src/static/app.js`
