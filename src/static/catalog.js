// Catalog — T9 ready-only grouped model picker. Fetches /api/v1/models,
// populates a grouped <select> (Vortex shared primary / Local fallback),
// and persists per-thread model selection.
//
// Kept out of app.js so app.js can stay focused on chat/streaming. Depends
// on window.TC (from threads.js), calls window.App.pollStatus and
// window.App.appendBubble lazily (defined in app.js, which loads AFTER).
window.Catalog = (function () {
  var TC = window.TC;

  // P2-8: per-thread model selection, persisted client-side. The server also
  // stores thread.model, but only once a send/create/rename/delete PUTs the
  // thread — a bare model switch (no send) was lost on reload. This
  // localStorage map (threadId -> modelId) records every selection immediately
  // and is the authority when restoring the active thread's model on reload.
  var THREAD_MODEL_STORE_KEY = 'testchat-thread-models';

  function readThreadModelStore() {
    try { return JSON.parse(localStorage.getItem(THREAD_MODEL_STORE_KEY)) || {}; }
    catch (e) { return {}; }
  }

  function storeThreadModel(threadId, model) {
    if (threadId == null) return;
    try {
      var map = readThreadModelStore();
      if (model) { map[String(threadId)] = model; } else { delete map[String(threadId)]; }
      localStorage.setItem(THREAD_MODEL_STORE_KEY, JSON.stringify(map));
    } catch (e) { /* private mode / quota — best-effort; server persistence still applies */ }
  }

  function storedThreadModel(threadId) {
    if (threadId == null) return '';
    return readThreadModelStore()[String(threadId)] || '';
  }

  var modelSelect = document.getElementById('model-select');
  var manageInVortex = document.getElementById('manage-in-vortex');

  function appendBubble(text, type) {
    if (window.App && window.App.appendBubble) {
      window.App.appendBubble(text, type);
    }
  }

  function pollStatus() {
    if (window.App && window.App.pollStatus) window.App.pollStatus();
  }

  function fetchModels() {
    return fetch('/api/v1/models')
      .then(function (r) {
        if (!r.ok) throw new Error('Failed to fetch models');
        return r.json();
      })
      .then(function (data) {
        var models = data.models || [];
        var router = data.router || { configured: false, reachable: false };
        populateModelOptions(models, router);
        return models;
      })
      .catch(function () {
        modelSelect.innerHTML = '<option value="">Failed to load models</option>';
        if (manageInVortex) manageInVortex.setAttribute('aria-disabled', 'true');
        pollStatus();
        return [];
      });
  }

  function populateModelOptions(models, router) {
    // Capture the old selection BEFORE clearing the select.
    var previous = modelSelect.value;
    if (!previous) {
      var activeThread = TC.threads.find(function (t) { return t.id === TC.activeThreadId; });
      var stored = storedThreadModel(TC.activeThreadId);
      if (stored) {
        previous = stored;
        if (activeThread) activeThread.model = stored;
      } else if (activeThread && activeThread.model) {
        previous = activeThread.model;
      }
    }

    modelSelect.innerHTML = '';

    // Partition by source === 'router'.
    var routerModels = [];
    var localModels = [];
    for (var i = 0; i < models.length; i++) {
      if (models[i].source === 'router') {
        routerModels.push(models[i]);
      } else {
        localModels.push(models[i]);
      }
    }

    // Vortex group: 'Vortex · shared · primary' first.
    var vortexGroup = document.createElement('optgroup');
    vortexGroup.label = 'Vortex · shared · primary';
    if (router.configured || routerModels.length) {
      if (!router.reachable) {
        vortexGroup.disabled = true;
      }
      for (var r = 0; r < routerModels.length; r++) {
        var ro = document.createElement('option');
        ro.value = routerModels[r].id;
        ro.textContent = '🟢 ' + routerModels[r].id;
        ro.dataset.loaded = router.reachable ? 'true' : 'false';
        vortexGroup.appendChild(ro);
      }
      modelSelect.appendChild(vortexGroup);
    }

    // Local group: 'Local · this machine · fallback' second, always enabled.
    var localGroup = document.createElement('optgroup');
    localGroup.label = 'Local · this machine · fallback';
    for (var l = 0; l < localModels.length; l++) {
      var lo = document.createElement('option');
      lo.value = localModels[l].id;
      lo.textContent = '🟢 ' + localModels[l].id;
      lo.dataset.loaded = 'true';
      localGroup.appendChild(lo);
    }
    modelSelect.appendChild(localGroup);

    // Determine if the previous selection's group is enabled.
    var previousEnabled = false;
    if (previous) {
      var prevOpt = Array.from(modelSelect.options).find(function (option) {
        return option.value === previous;
      });
      if (prevOpt) {
        var prevGroup = prevOpt.parentElement;
        if (prevGroup && prevGroup.tagName === 'OPTGROUP') {
          previousEnabled = !prevGroup.disabled;
        } else {
          previousEnabled = true;
        }
      }
    }

    // Choose the selection.
    var chosen = '';
    if (previous && previousEnabled) {
      chosen = previous;
    } else {
      // First enabled option.
      var allOpts = modelSelect.querySelectorAll('option');
      for (var a = 0; a < allOpts.length; a++) {
        var grp = allOpts[a].parentElement;
        if (grp && grp.tagName === 'OPTGROUP' && grp.disabled) continue;
        chosen = allOpts[a].value;
        break;
      }
    }

    if (!chosen) {
      var ph = document.createElement('option');
      ph.value = '';
      ph.textContent = 'Select model...';
      modelSelect.insertBefore(ph, modelSelect.firstChild);
      modelSelect.value = '';
    } else {
      modelSelect.value = chosen;
    }

    // Synchronize the active thread.model to the chosen value.
    var activeThread2 = TC.threads.find(function (t) { return t.id === TC.activeThreadId; });
    if (activeThread2) activeThread2.model = modelSelect.value || '';

    modelSelect.classList.toggle('select-empty', !modelSelect.value);

    // Synchronize manage-in-vortex reachability.
    if (manageInVortex) {
      if (router && router.reachable) {
        manageInVortex.removeAttribute('aria-disabled');
      } else {
        manageInVortex.setAttribute('aria-disabled', 'true');
      }
    }

    // Poll status so status/source/Send state updates immediately.
    pollStatus();
  }

  function refreshModels() {
    return fetchModels();
  }

  // Manage-in-vortex link: prevent navigation while disabled.
  if (manageInVortex) {
    manageInVortex.addEventListener('click', function (e) {
      if (manageInVortex.getAttribute('aria-disabled') === 'true') {
        e.preventDefault();
      }
    });
  }

  modelSelect.addEventListener('change', function () {
    modelSelect.classList.toggle('select-empty', !modelSelect.value);
    var thread = TC.threads.find(function (t) { return t.id === TC.activeThreadId; });
    if (thread) thread.model = modelSelect.value;
    storeThreadModel(TC.activeThreadId, modelSelect.value);
    pollStatus();
  });

  return {
    fetchModels: fetchModels,
    refreshModels: refreshModels,
    storedThreadModel: storedThreadModel,
    storeThreadModel: storeThreadModel
  };
})();
