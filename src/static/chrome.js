// Chrome — themes, focus mode, settings modal, and generic modal chrome
// (backdrop-click dismissal, Escape handler). Kept out of app.js so the
// chat surface there stays about model selection, streaming, and bubbles.
//
// Depends only on DOM ids present in index.html at load time; grabs
// appendBubble lazily through window.App because that function lives in
// app.js and app.js is script-loaded AFTER this file.
window.Chrome = (function () {
  var themeToggle = document.getElementById('theme-toggle');

  var THEMES = ['light', 'dark', 'matrix', 'phosphor', 'midnight', 'neon', 'crisp', 'ember', 'graphite-amber', 'graphite-forest'];
  var THEME_ICONS = { light: '☀️', dark: '🌙', matrix: '💊', phosphor: '>_ ', midnight: '🌃', neon: '⚡', crisp: '🌤', ember: '🔥', 'graphite-amber': '🔶', 'graphite-forest': '🌲' };

  function applyTheme(theme) {
    if (THEMES.indexOf(theme) === -1) theme = 'light';
    document.documentElement.setAttribute('data-theme', theme);
    if (theme === 'matrix') {
      if (typeof window.MatrixRain !== 'undefined') { window.MatrixRain.start(); }
    } else {
      if (typeof window.MatrixRain !== 'undefined') { window.MatrixRain.stop(); }
    }
    var titlebar = document.querySelector('[data-testid="terminal-titlebar"]');
    if (titlebar) {
      titlebar.style.display = theme === 'phosphor' ? 'flex' : 'none';
    }
    themeToggle.textContent = THEME_ICONS[theme];
    try { localStorage.setItem('testchat-theme', theme); } catch (e) { /* private mode */ }
  }

  themeToggle.addEventListener('click', function () {
    var current = document.documentElement.getAttribute('data-theme') || 'light';
    applyTheme(THEMES[(THEMES.indexOf(current) + 1) % THEMES.length]);
  });

  try { applyTheme(localStorage.getItem('testchat-theme') || 'light'); } catch (e) { applyTheme('light'); }

  // Focus mode
  var fullscreenToggle = document.getElementById('fullscreen-toggle');
  var statusTps = document.getElementById('status-tps');

  function fullscreenEl() {
    return document.fullscreenElement || document.webkitFullscreenElement || null;
  }

  function exitZen() {
    document.body.classList.remove('zen');
    if (!fullscreenEl()) return;
    if (document.exitFullscreen) {
      document.exitFullscreen().catch(function () { /* already out of fullscreen — nothing to exit */ });
    } else if (document.webkitExitFullscreen) {
      document.webkitExitFullscreen();
    }
  }

  function fsDiag(lastErr, method) {
    var d = document;
    var activation = 'n/a';
    if (navigator.userActivation) activation = String(navigator.userActivation.isActive);
    var msg = lastErr && lastErr.message ? lastErr.message : String(lastErr || 'unknown');
    var info = msg +
      ' | via: ' + (method || '?') +
      ', gestureActive: ' + activation +
      ', fullscreenEnabled: ' + (d.fullscreenEnabled !== undefined ? d.fullscreenEnabled : (d.webkitFullscreenEnabled !== undefined ? d.webkitFullscreenEnabled : 'unknown'));
    try { console.warn('fullscreen failed:', info); } catch (e) { /* console unavailable — diag is best-effort */ }
    if (statusTps) statusTps.textContent = 'fullscreen: ' + msg;
    if (window.App && window.App.appendBubble) {
      window.App.appendBubble('Browser fullscreen failed — ' + info, 'error');
    }
  }

  fullscreenToggle.addEventListener('click', function () {
    var gestureAtClick = navigator.userActivation ? String(navigator.userActivation.isActive) : 'n/a';
    var el = document.documentElement || document.body;
    var methodName = el.webkitRequestFullscreen ? 'webkitRequestFullscreen' : (el.requestFullscreen ? 'requestFullscreen' : null);
    var label = methodName + ' on ' + (el.className || el.tagName) + ', gestureAtClick: ' + gestureAtClick;
    if (methodName) {
      try {
        var p = el[methodName]();
        if (p && p.catch) {
          p.catch(function (err) { fsDiag(err, label); });
        } else {
          setTimeout(function () {
            if (!fullscreenEl()) fsDiag('request returned without entering fullscreen', label);
          }, 400);
        }
      } catch (err) {
        fsDiag(err, label);
      }
    } else {
      fsDiag('no Fullscreen API method on element', label);
    }
    document.body.classList.add('zen');
  });

  function onFullscreenChange() {
    if (!fullscreenEl()) document.body.classList.remove('zen');
  }

  document.addEventListener('fullscreenchange', onFullscreenChange);
  document.addEventListener('webkitfullscreenchange', onFullscreenChange);

  // Settings modal
  var settingsToggle = document.getElementById('settings-toggle');
  var settingsModal = document.getElementById('settings-modal');
  var systemPromptInput = document.getElementById('system-prompt-input');

  function openSettings() {
    fetch('/api/v1/settings')
      .then(function (r) { return r.json(); })
      .then(function (d) { systemPromptInput.value = d.system_prompt || ''; })
      .catch(function () { systemPromptInput.value = ''; })
      .finally(function () {
        settingsModal.hidden = false;
        systemPromptInput.focus();
      });
  }

  function closeSettings() {
    settingsModal.hidden = true;
  }

  settingsToggle.addEventListener('click', openSettings);
  document.getElementById('settings-cancel').addEventListener('click', closeSettings);
  document.getElementById('settings-save').addEventListener('click', function () {
    fetch('/api/v1/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ system_prompt: systemPromptInput.value })
    }).then(closeSettings).catch(closeSettings);
  });
  settingsModal.addEventListener('click', function (e) {
    if (e.target === settingsModal) closeSettings();
  });

  // Confirm-modal dismissals: click on the overlay backdrop = cancel.
  // Each modal keeps its cancel button as the primary dismiss path;
  // this is a convenience mirror, so it just triggers that button.
  var loadConfirmModal = document.getElementById('load-confirm-modal');
  var loadCancelBtn = document.getElementById('load-cancel');
  var unloadConfirmModal = document.getElementById('unload-confirm-modal');
  var unloadCancelBtn = document.getElementById('unload-cancel');
  var deleteConfirmModal = document.getElementById('delete-confirm-modal');
  var deleteCancelBtn = document.getElementById('delete-cancel');

  loadConfirmModal.addEventListener('click', function (e) {
    if (e.target === loadConfirmModal) loadCancelBtn.click();
  });
  unloadConfirmModal.addEventListener('click', function (e) {
    if (e.target === unloadConfirmModal) unloadCancelBtn.click();
  });
  deleteConfirmModal.addEventListener('click', function (e) {
    if (e.target === deleteConfirmModal) deleteCancelBtn.click();
  });

  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    if (!settingsModal.hidden) {
      closeSettings();
    } else if (!loadConfirmModal.hidden) {
      loadCancelBtn.click();
    } else if (!unloadConfirmModal.hidden) {
      unloadCancelBtn.click();
    } else if (!deleteConfirmModal.hidden) {
      deleteCancelBtn.click();
    } else if (document.body.classList.contains('zen')) {
      exitZen();
    }
  });

  return {};
})();
