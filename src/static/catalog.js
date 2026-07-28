// Catalog — model dropdown lifecycle. Fetch and populate the <select>,
// eject/unload flow, and the change-handler that offers a load confirm for
// unloaded picks (with AC-28 mid-chat selector-lock coupling preserved).
//
// Kept out of app.js so app.js can stay focused on chat/streaming. Depends
// on window.TC (from threads.js), calls window.App.pollStatus and
// window.App.appendBubble lazily (defined in app.js, which loads AFTER).
window.Catalog = (function () {
  var TC = window.TC;
  var previousModelValue = null;

  var modelSelect = document.getElementById('model-select');
  var ejectModelBtn = document.getElementById('eject-model-btn');
  var loadConfirmModal = document.getElementById('load-confirm-modal');
  var loadConfirmBtn = document.getElementById('load-confirm');
  var loadCancelBtn = document.getElementById('load-cancel');
  var loadConfirmText = document.getElementById('load-confirm-text');
  var unloadConfirmModal = document.getElementById('unload-confirm-modal');
  var unloadConfirmBtn = document.getElementById('unload-confirm');
  var unloadCancelBtn = document.getElementById('unload-cancel');
  var unloadConfirmText = document.getElementById('unload-confirm-text');
  var statusRam = document.getElementById('status-ram');

  function appendBubble(text, type) {
    if (window.App && window.App.appendBubble) {
      window.App.appendBubble(text, type);
    }
  }

  function pollStatus() {
    if (window.App && window.App.pollStatus) window.App.pollStatus();
  }

  function fetchModels() {
    var lmPromise = fetch('/api/v1/models').then(function (r) {
      if (!r.ok) throw new Error('Failed to fetch models');
      return r.json();
    });
    var catalogPromise = fetch('/api/v1/models/catalog').then(function (r) {
      if (!r.ok) throw new Error('Failed to fetch catalog');
      return r.json();
    });

    Promise.all([lmPromise, catalogPromise])
      .then(function (results) {
        var lmData = results[0];
        var catalogData = results[1];
        var lmModels = lmData.models || [];
        var catalogModels = catalogData ? (catalogData.models || []) : [];
        var options = [];
        for (var i = 0; i < lmModels.length; i++) {
          options.push({ id: lmModels[i].id, loaded: true });
        }
        for (var j = 0; j < catalogModels.length; j++) {
          options.push({ id: catalogModels[j].id, loaded: catalogModels[j].loaded === true });
        }
        populateModelOptions(options);
      })
      .catch(function () {
        return lmPromise.then(function (lmData) {
          var lmModels = lmData.models || [];
          var options = [];
          for (var i = 0; i < lmModels.length; i++) {
            options.push({ id: lmModels[i].id, loaded: true });
          }
          populateModelOptions(options);
        }).catch(function () {
          modelSelect.innerHTML = '<option value="">Failed to load models</option>';
        });
      });
  }

  function populateModelOptions(models) {
    var previous = modelSelect.value;
    if (!previous) {
      var activeThread = TC.threads.find(function (t) { return t.id === TC.activeThreadId; });
      if (activeThread && activeThread.model) previous = activeThread.model;
    }
    modelSelect.innerHTML = '';

    TC.scriptModelLoaded = false;
    for (var c = 0; c < models.length; c++) {
      if (models[c].loaded === true) { TC.scriptModelLoaded = true; break; }
    }
    ejectModelBtn.disabled = !TC.scriptModelLoaded;
    ejectModelBtn.hidden = !TC.scriptModelLoaded;

    if (models.length === 0) {
      var opt = document.createElement('option');
      opt.value = '';
      opt.textContent = 'No models available';
      modelSelect.appendChild(opt);
      return;
    }

    for (var m = 0; m < models.length; m++) {
      var o = document.createElement('option');
      var id = models[m].id;
      var loaded = models[m].loaded;
      o.value = id;
      o.dataset.loaded = loaded ? 'true' : 'false';
      var prefix = loaded ? '🟢 ' : '○ ';
      if (id === previous) prefix = '✓ ' + prefix;
      o.textContent = prefix + id;
      modelSelect.appendChild(o);
    }

    var opts = modelSelect.options;
    var matched = false;
    for (var n = 0; n < opts.length; n++) {
      if (opts[n].value === previous) {
        modelSelect.value = previous;
        var thread2 = TC.threads.find(function (t) { return t.id === TC.activeThreadId; });
        if (thread2) thread2.model = previous;
        matched = true;
        break;
      }
    }
    if (!matched) {
      for (var q = 0; q < models.length; q++) {
        if (models[q].loaded) {
          modelSelect.value = models[q].id;
          var t = TC.threads.find(function (t) { return t.id === TC.activeThreadId; });
          if (t) t.model = models[q].id;
          matched = true;
          break;
        }
      }
    }
    if (!matched) {
      var ph = document.createElement('option');
      ph.value = '';
      ph.disabled = true;
      ph.hidden = true;
      ph.textContent = 'Select model...';
      modelSelect.insertBefore(ph, modelSelect.firstChild);
      modelSelect.value = '';
      var t2 = TC.threads.find(function (t) { return t.id === TC.activeThreadId; });
      if (t2) t2.model = '';
    }
    if (previous && !opts.length) {
      var thread3 = TC.threads.find(function (t) { return t.id === TC.activeThreadId; });
      if (thread3) thread3.model = modelSelect.value || '';
    }
    modelSelect.classList.toggle('select-empty', !modelSelect.value);
  }

  function refreshModels() {
    fetchModels();
  }

  ejectModelBtn.addEventListener('click', function () {
    fetch('/api/v1/models/catalog')
      .then(function (response) {
        if (!response.ok) throw new Error('Failed to fetch catalog');
        return response.json();
      })
      .then(function (data) {
        var models = data.models || [];
        var loadedModel = null;
        for (var i = 0; i < models.length; i++) {
          if (models[i].loaded === true) {
            loadedModel = models[i];
            break;
          }
        }
        if (!loadedModel) return;
        unloadConfirmModal.dataset.modelId = loadedModel.id;
        unloadConfirmText.textContent = 'Unload ' + loadedModel.id + '?';
        unloadConfirmModal.hidden = false;
      })
      .catch(function () { /* silently ignore catalog fetch failures */ });
  });

  unloadCancelBtn.addEventListener('click', function () {
    unloadConfirmModal.hidden = true;
  });

  unloadConfirmBtn.addEventListener('click', function () {
    unloadConfirmModal.hidden = true;
    var id = unloadConfirmModal.dataset.modelId || '';
    fetch('/api/v1/script-models/' + encodeURIComponent(id) + '/unload', { method: 'POST' })
      .then(function (response) {
        if (!response.ok) throw new Error('Failed to unload model');
        refreshModels();
        pollStatus();
      })
      .catch(function (err) {
        appendBubble(err.message || 'Failed to unload model', 'error');
      });
  });

  // Native <select> fires 'change' AFTER value updates, so capture the
  // pre-change value on focus/mousedown — needed so load-cancel can
  // actually revert (bug: prior was reading the just-picked value).
  var ejectHideTimer = null;
  modelSelect.addEventListener('focus', function () {
    previousModelValue = modelSelect.value;
    ejectModelBtn.hidden = false;
    if (ejectHideTimer) { clearTimeout(ejectHideTimer); ejectHideTimer = null; }
  });
  modelSelect.addEventListener('blur', function () {
    ejectHideTimer = setTimeout(function () {
      ejectModelBtn.hidden = !TC.scriptModelLoaded;
      ejectHideTimer = null;
    }, 200);
  });
  modelSelect.addEventListener('mousedown', function () {
    previousModelValue = modelSelect.value;
  });

  modelSelect.addEventListener('change', function () {
    modelSelect.classList.toggle('select-empty', !modelSelect.value);
    var selected = modelSelect.options[modelSelect.selectedIndex];
    if (selected && selected.dataset.loaded === 'false') {
      // Overlapping-load guard: mid-load thread-switch can re-enable the
      // selector on an unlocked thread, letting a second load start
      // before the first .finally fires. Both loads'
      // _unload_other_script_models then race for the same process
      // handle. Only unloaded picks can start a load, so loaded-model
      // selections stay usable during the (up to 180s) load window.
      if (TC.modelLoading) {
        modelSelect.value = previousModelValue;
        modelSelect.classList.toggle('select-empty', !modelSelect.value);
        return;
      }
      var prior = previousModelValue;
      var id = modelSelect.value;
      loadConfirmText.textContent = 'Start ' + id + '? Uses significant RAM. ' + statusRam.textContent;
      loadConfirmModal.hidden = false;
      pollStatus();
      loadCancelBtn.onclick = function () {
        loadConfirmModal.hidden = true;
        modelSelect.value = prior;
        modelSelect.classList.toggle('select-empty', !modelSelect.value);
        pollStatus();
      };
      loadConfirmBtn.onclick = function () {
        loadConfirmModal.hidden = true;
        modelSelect.disabled = true;
        TC.modelLoading = true;
        var opt = modelSelect.options[modelSelect.selectedIndex];
        var baseText = opt.value;
        var interval = setInterval(function () {
          var current = opt.textContent;
          if (current.indexOf('🟢 ') === 0) {
            opt.textContent = '○ ' + baseText;
          } else {
            opt.textContent = '🟢 ' + baseText;
          }
        }, 600);
        fetch('/api/v1/script-models/' + encodeURIComponent(id) + '/load', { method: 'POST' })
          .then(function (response) {
            if (!response.ok) throw new Error('Failed to load model');
            clearInterval(interval);
            previousModelValue = id;
            refreshModels();
          })
          .catch(function (err) {
            clearInterval(interval);
            // The blink can stop on the 🟢 half-cycle; a failed model
            // must not sit in the list looking loaded.
            opt.textContent = '○ ' + baseText;
            modelSelect.value = prior;
            appendBubble(err.message || 'Failed to load model', 'error');
          })
          .finally(function () {
            TC.modelLoading = false;
            var active = TC.threads.find(function (t) { return t.id === TC.activeThreadId; });
            modelSelect.disabled = active ? !!active.locked : false;
            pollStatus();
          });
      };
    } else {
      previousModelValue = modelSelect.value;
      var thread = TC.threads.find(function (t) { return t.id === TC.activeThreadId; });
      if (thread) thread.model = modelSelect.value;
      pollStatus();
    }
  });

  return {
    fetchModels: fetchModels,
    refreshModels: refreshModels
  };
})();
