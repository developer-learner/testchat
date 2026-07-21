    (function () {
      var TC = window.TC;
      var MD = window.MD;
      var Threads = window.Threads;
      var FALLBACK_REPLY = 'Sorry, something went wrong. Please try again.';

      var form = document.getElementById('chat-form');
      var input = document.getElementById('message-input');
      var container = document.getElementById('chat-container');
      var sendBtn = document.getElementById('send-btn');
      var thinkToggle = document.getElementById('think-toggle');
      var webToggle = document.getElementById('web-toggle');
      var webArmed = false;
      webToggle.addEventListener('click', function () {
        webArmed = !webArmed;
        webToggle.classList.toggle('active', webArmed);
      });
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
      var newThreadBtn = document.getElementById('new-thread-btn');
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
        appendBubble('Browser fullscreen failed — ' + info, 'error');
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

      var replyText = '';
      var chunkCount = 0;
      var streamStartMs = 0;
      var tpsTimer = null;
      var statusModel = document.getElementById('status-model');
      var statusRam = document.getElementById('status-ram');
      var statusTps = document.getElementById('status-tps');

      function pollStatus() {
        // Status glyph must reflect ACTUAL load state (dataset.loaded on the
        // selected option), not merely that a dropdown value exists — otherwise
        // an unloaded script model selected + never confirmed reads as loaded.
        var currentOpt = modelSelect.options[modelSelect.selectedIndex];
        var currentLoaded = !!(currentOpt && currentOpt.dataset.loaded === 'true');
        if (!modelSelect.value) {
          statusModel.textContent = 'no model';
        } else {
          statusModel.textContent = (currentLoaded ? '● ' : '○ ') + modelSelect.value;
        }
        statusModel.classList.toggle('ok', currentLoaded);
        // Send disabled unless a loaded model is selected. Guard: during
        // streaming the Send button IS the Stop button — must stay clickable.
        if (!TC.streaming) {
          sendBtn.disabled = !currentLoaded;
        }
        // Eject unloads the loaded SCRIPT model, never the selection — so it
        // is enabled iff the catalog reports one loaded (LM Studio models are
        // not ours to unload; selecting one must not light the button).
        ejectModelBtn.disabled = !TC.scriptModelLoaded;
        fetch('/api/v1/status')
          .then(function (r) { return r.json(); })
          .then(function (d) {
            var ram = 'RAM ' + d.ram_used_gb + '/' + d.ram_total_gb + ' GB';
            if (d.models && d.models.length) {
              d.models.forEach(function (m) {
                if (m.loaded && m.rss_gb) ram += ' · ' + m.id + ' ' + m.rss_gb + ' GB';
              });
            } else if (d.nemotron_loaded && d.nemotron_rss_gb) {
              ram += ' · nemotron ' + d.nemotron_rss_gb + ' GB';
            }
            if (typeof d.loadable_gb === 'number') {
              ram += ' · ~' + d.loadable_gb + ' GB loadable';
            }
            statusRam.textContent = ram;
            webToggle.disabled = !d.web_configured;
            if (webToggle.disabled) { webArmed = false; webToggle.classList.remove('active'); }
          })
          .catch(function () { statusRam.textContent = ''; });
      }

      setInterval(pollStatus, 5000);
      pollStatus();

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
      document.addEventListener('keydown', function (e) {
        if (e.key !== 'Escape') return;
        if (!settingsModal.hidden) {
          closeSettings();
        } else if (document.body.classList.contains('zen')) {
          exitZen();
        }
      });

      // Bubble helpers
      function appendBubble(text, type) {
        var bubble = document.createElement('div');
        bubble.className = 'chat-bubble ' + type;
        bubble.textContent = text;
        bubble.setAttribute('data-testid', type === 'user' ? 'msg-user' : 'msg-assistant');
        container.appendChild(bubble);
        scrollToBottom();
        return bubble;
      }

      function scrollToBottom() {
        container.scrollTop = container.scrollHeight;
      }

      function renderReply(bubble, text, live) {
        // Qwen/Alibaba models emit citations as 【N†anchor】; normalize to [N]
        // so users see plain numbers matching the source list under the reply.
        text = text.replace(/【(\d+)[†‡]?[^】]*】/g, '[$1]');
        var html = MD.renderThink(text);
        var visible = html.replace(/<span class=\"think-content\"[^>]*>[\s\S]*?<\/span>/g, '').replace(/<[^>]+>/g, '').trim();
        bubble.innerHTML = visible === '' ? 'thinking...' : html;
        bubble.dataset.raw = MD.stripThink(text);
        if (live) appendStreamCursor(bubble);
      }

      function appendStreamCursor(bubble) {
        var el = bubble;
        while (el.lastElementChild && el.lastElementChild.tagName !== 'HR' &&
               !el.lastElementChild.classList.contains('copy-btn')) {
          el = el.lastElementChild;
        }
        var c = document.createElement('span');
        c.className = 'stream-cursor';
        el.appendChild(c);
      }

      // Enter submits, Shift+Enter inserts newline. Also auto-grow the
      // textarea up to ~40vh so a multi-line paste (markdown blocks, code)
      // is readable without hiding the messages behind a scrolling wall.
      function autogrow() {
        input.style.height = 'auto';
        var cap = Math.round(window.innerHeight * 0.4);
        input.style.height = Math.min(input.scrollHeight, cap) + 'px';
      }
      input.addEventListener('input', autogrow);
      input.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
          e.preventDefault();
          form.requestSubmit();
        }
      });
      autogrow();

      // Stop button
      sendBtn.addEventListener('click', function () {
        if (TC.streaming && TC.currentController) TC.currentController.abort();
      });

      // Chat form submit
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        if (TC.streaming) return;
        var message = input.value.trim();
        if (!message) return;

        var currentThread = TC.threads.find(function (t) { return t.id === TC.activeThreadId; });

        if (currentThread.messages.length === 0) {
          Threads.updateTitle(currentThread, message);
        }

        var userBubble = appendBubble(message, 'user');
        Threads.addBubbleChrome(userBubble, message, Date.now() / 1000, '');
        input.value = '';
        autogrow();
        TC.streaming = true;
        TC.streamingThreadId = currentThread.id;
        TC.currentController = new AbortController();
        // The stream outlives UI state: capture the model now so a mid-stream
        // thread switch (which rewrites the selector) can't mislabel the reply.
        var streamModel = modelSelect.value;
        sendBtn.type = 'button';
        sendBtn.textContent = 'Stop';
        sendBtn.classList.add('stop');
        chunkCount = 0;
        streamStartMs = Date.now();
        var lastTpsCount = 0;
        tpsTimer = setInterval(function () {
          statusTps.textContent = (chunkCount - lastTpsCount) + ' tok/s';
          lastTpsCount = chunkCount;
        }, 1000);

        var replyBubble = document.createElement('div');
        replyBubble.className = 'chat-bubble reply';
        replyBubble.setAttribute('data-testid', 'msg-assistant');
        container.appendChild(replyBubble);
        replyBubble.textContent = 'thinking...';
        // Switching away wipes the container; keep handles so switching back
        // mid-stream can re-attach the live pair instead of orphaning it.
        TC.liveBubbles = [userBubble, replyBubble];
        replyText = '';
        var userStored = false;

        var streamEnded = false;
        var renderQueued = false;
        function queueRender() {
          if (renderQueued) return;
          renderQueued = true;
          setTimeout(function () {
            renderQueued = false;
            if (streamEnded) return;
            renderReply(replyBubble, replyText, true);
            scrollToBottom();
          }, 30);
        }

        currentThread.model = modelSelect.value;

        var bodyObj = { message: message, history: currentThread.messages.map(function (m) { return { role: m.role, content: MD.stripThink(m.content) }; }) };
        if (modelSelect.value) {
          bodyObj.model = modelSelect.value;
        }
        if (webArmed) bodyObj.web = true;
        webArmed = false;
        webToggle.classList.remove('active');
        var pendingSources = [];
        var pendingNotice = '';

        fetch('/api/v1/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(bodyObj),
          signal: TC.currentController.signal
        })
        .then(function (response) {
          if (!response.ok) {
            throw new Error('Request failed with status ' + response.status);
          }

          var reader = response.body.getReader();
          var decoder = new TextDecoder('utf-8');
          var buffer = '';

          function processFrame(frame) {
            if (!frame || !frame.trim()) return;

            var eventType = '';
            var dataStr = '';

            frame.split('\n').forEach(function (line) {
              if (line.indexOf('event:') === 0) {
                eventType = line.substring(6).trim();
              } else if (line.indexOf('data:') === 0) {
                dataStr += line.substring(5).trim();
              }
            });

            if (!eventType) return;

            if (eventType === 'sources') {
              try {
                var sd = JSON.parse(dataStr);
                pendingSources = sd.sources || [];
                pendingNotice = sd.notice || '';
              } catch (err) { /* sources JSON parse failure — ignore, sources stay empty */ }
            } else if (eventType === 'token') {
              try {
                var parsed = JSON.parse(dataStr);
                replyText += parsed.content;
              } catch (err) {
                replyText += dataStr;
              }
              chunkCount++;
              queueRender();
            } else if (eventType === 'think') {
              try {
                var parsed = JSON.parse(dataStr);
                replyText += '<think>' + parsed.content + '</think>';
              } catch (err) {
                replyText += '<think>' + dataStr + '</think>';
              }
              chunkCount++;
              queueRender();
            } else if (eventType === 'done') {
              streamEnded = true;
              userStored = true;
              var now = Date.now() / 1000;
              currentThread.messages.push({ role: 'user', content: message, ts: now });
              var am = { role: 'assistant', content: replyText, ts: now, model: streamModel || '' };
              if (pendingSources.length) am.sources = pendingSources.map(function (s) { return { title: s.title, url: s.url }; });
              currentThread.messages.push(am);
              if (pendingSources.length || pendingNotice) setTimeout(function () { Threads.addSources(replyBubble, pendingSources, pendingNotice); }, 0);
              renderReply(replyBubble, replyText);
              Threads.addBubbleChrome(replyBubble, MD.stripThink(replyText), now, streamModel || '', currentThread.messages.length - 1);
              Threads.maybeRetitle(currentThread);
              Threads.persistThreads();
            } else if (eventType === 'error') {
              streamEnded = true;
              if (!userStored) { currentThread.messages.push({ role: 'user', content: message, ts: Date.now() / 1000 }); userStored = true; }
              var errMsg = FALLBACK_REPLY;
              try {
                var errData = JSON.parse(dataStr);
                errMsg = errData.message || FALLBACK_REPLY;
              } catch (err) {
                errMsg = dataStr || FALLBACK_REPLY;
              }
              // Mirror the abort path: a stream that dies after content keeps
              // the partial reply (the backend pins error-after-tokens for a
              // dropped stream); only a token-less failure becomes a bare
              // error bubble.
              var errPartial = MD.stripThink(replyText).replace(/^\s+|\s+$/g, '');
              if (errPartial) {
                var errNow = Date.now() / 1000;
                currentThread.messages.push({ role: 'assistant', content: errPartial, ts: errNow, model: streamModel || '' });
                renderReply(replyBubble, replyText);
                Threads.addBubbleChrome(replyBubble, errPartial, errNow, streamModel || '', currentThread.messages.length - 1);
                // Only surface the transient error bubble if the stream's
                // thread is on screen — never inject it into another thread.
                if (replyBubble.parentNode) appendBubble(errMsg, 'error');
              } else {
                replyBubble.className = 'chat-bubble error';
                replyBubble.textContent = errMsg;
              }
              Threads.persistThreads();
            }
          }

          function read() {
            return reader.read().then(function (result) {
              if (result.done) {
                var remaining = buffer.trim();
                if (remaining) {
                  processFrame(remaining);
                }
                return;
              }

              buffer += decoder.decode(result.value, { stream: true });

              var parts = buffer.split('\n\n');
              for (var i = 0; i < parts.length - 1; i++) {
                processFrame(parts[i].trim());
              }
              buffer = parts[parts.length - 1];

              return read();
            });
          }

          // Lock the thread the stream belongs to, not whichever thread is
          // active when the headers arrive.
          Threads.lockThread(currentThread);
          return read();
        })
        .catch(function (err) {
          streamEnded = true;
          if (!userStored) { currentThread.messages.push({ role: 'user', content: message, ts: Date.now() / 1000 }); userStored = true; }
          if (err && err.name === 'AbortError') {
            var partial = MD.stripThink(replyText).replace(/^\s+|\s+$/g, '');
            if (partial) {
              currentThread.messages.push({ role: 'assistant', content: partial, ts: Date.now() / 1000, model: streamModel || '' });
              renderReply(replyBubble, replyText);
            } else if (replyBubble.parentNode) {
              replyBubble.parentNode.removeChild(replyBubble);
            }
          } else {
            replyBubble.className = 'chat-bubble error';
            replyBubble.textContent = FALLBACK_REPLY;
          }
          Threads.persistThreads();
        })
        .finally(function () {
          TC.streaming = false;
          TC.streamingThreadId = null;
          TC.liveBubbles = null;
          TC.currentController = null;
          // If the stream's thread was deleted mid-stream, its bubbles are
          // stale DOM in whatever thread is now active — drop them.
          if (!TC.threads.some(function (t) { return t.id === currentThread.id; })) {
            if (userBubble.parentNode) userBubble.parentNode.removeChild(userBubble);
            if (replyBubble.parentNode) replyBubble.parentNode.removeChild(replyBubble);
          } else if (currentThread.id !== TC.activeThreadId) {
            // Finished while another thread is on screen: re-render that
            // thread if the finished bubbles leaked into its container.
            if (userBubble.parentNode || replyBubble.parentNode) {
              Threads.switchThread(TC.activeThreadId);
            }
          }
          sendBtn.type = 'submit';
          sendBtn.textContent = 'Send';
          sendBtn.classList.remove('stop');
          sendBtn.disabled = false;
          if (tpsTimer) { clearInterval(tpsTimer); tpsTimer = null; }
          var dur = (Date.now() - streamStartMs) / 1000;
          if (chunkCount && dur > 0.5) {
            statusTps.textContent = 'avg ' + (chunkCount / dur).toFixed(1) + ' tok/s';
          }
          input.focus();
        });
      });

      // Per-message hover actions (event delegation)
      container.addEventListener('click', function (e) {
        var btn = e.target;
        if (!btn.classList) return;
        if (btn.classList.contains('b-copy')) {
          copyToClipboard(btn.closest('.chat-bubble').dataset.raw || '', btn);
        } else if (btn.classList.contains('b-del')) {
          Threads.deleteMessagePair(parseInt(btn.getAttribute('data-idx'), 10));
        }
      });

      function copyToClipboard(text, btn) {
        var flash = function () {
          btn.classList.add('done');
          setTimeout(function () { btn.classList.remove('done'); }, 1200);
        };
        var legacy = function () {
          var ta = document.createElement('textarea');
          ta.value = text;
          document.body.appendChild(ta);
          ta.select();
          try { if (document.execCommand('copy')) flash(); } catch (err) { /* legacy-copy fallback failed — no flash is the honest signal */ }
          document.body.removeChild(ta);
        };
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(flash).catch(legacy);
        } else {
          legacy();
        }
      }

      // Code block copy (event delegation)
      container.addEventListener('click', function (e) {
        var btn = e.target;
        if (!btn.classList || !btn.classList.contains('copy-btn')) return;
        var codeEl = btn.parentNode.querySelector('code');
        if (!codeEl) return;
        var text = codeEl.textContent;
        var copied = function () {
          btn.textContent = 'copied!';
          setTimeout(function () { btn.textContent = 'copy'; }, 1200);
        };
        var legacyCopy = function () {
          var ta = document.createElement('textarea');
          ta.value = text;
          document.body.appendChild(ta);
          ta.select();
          try { if (document.execCommand('copy')) copied(); } catch (err) { /* legacy-copy fallback failed — no copied-state is the honest signal */ }
          document.body.removeChild(ta);
        };
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(copied).catch(legacyCopy);
        } else {
          legacyCopy();
        }
      });

      thinkToggle.addEventListener('click', function () {
        TC.showThinking = !TC.showThinking;
        thinkToggle.classList.toggle('on');
        container.classList.toggle('show-thinking');
      });

      newThreadBtn.addEventListener('click', function () {
        Threads.createThread();
      });

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
            populateModelOptions(lmData, catalogData);
          })
          .catch(function () {
            return lmPromise.then(function (lmData) {
              populateModelOptions(lmData, null);
            }).catch(function () {
              modelSelect.innerHTML = '<option value="">Failed to load models</option>';
            });
          });
      }

      function populateModelOptions(lmData, catalogData) {
        var previous = modelSelect.value;
        // Startup race: if the threads hydrate resolves before the first
        // models response, restoreThreadModelState's value-set silently
        // no-ops (no matching option yet). Fall back to the active thread's
        // saved model so the selection still lands once options exist.
        if (!previous) {
          var activeThread = TC.threads.find(function (t) { return t.id === TC.activeThreadId; });
          if (activeThread && activeThread.model) previous = activeThread.model;
        }
        modelSelect.innerHTML = '';
        var lmModels = lmData.models || [];
        var catalogModels = catalogData ? (catalogData.models || []) : [];

        TC.scriptModelLoaded = false;
        for (var c = 0; c < catalogModels.length; c++) {
          if (catalogModels[c].loaded === true) { TC.scriptModelLoaded = true; break; }
        }
        ejectModelBtn.disabled = !TC.scriptModelLoaded;
        ejectModelBtn.hidden = !TC.scriptModelLoaded;

        var lmMap = {};
        for (var k = 0; k < lmModels.length; k++) {
          lmMap[lmModels[k].id] = true;
        }

        var options = [];
        for (var i = 0; i < lmModels.length; i++) {
          options.push({ id: lmModels[i].id, loaded: true });
        }
        for (var j = 0; j < catalogModels.length; j++) {
          if (!lmMap[catalogModels[j].id]) {
            options.push({ id: catalogModels[j].id, loaded: catalogModels[j].loaded === true });
          }
        }

        if (options.length === 0) {
          var opt = document.createElement('option');
          opt.value = '';
          opt.textContent = 'No models available';
          modelSelect.appendChild(opt);
          return;
        }

        for (var m = 0; m < options.length; m++) {
          var o = document.createElement('option');
          var id = options[m].id;
          var loaded = options[m].loaded;
          o.value = id;
          o.dataset.loaded = loaded ? 'true' : 'false';
          var prefix = loaded ? '\ud83d\udfe2 ' : '\u25cb ';
          o.textContent = prefix + id;
          modelSelect.appendChild(o);
        }

        var opts = modelSelect.options;
        for (var n = 0; n < opts.length; n++) {
          if (opts[n].value === previous) {
            modelSelect.value = previous;
            // AC-100 (v57): no label glyph for the selection \u2014 the native
            // <select> already marks it, and a "\u2713 " prefix duplicated
            // the OS checkmark on macOS.
            var thread2 = TC.threads.find(function (t) { return t.id === TC.activeThreadId; });
            if (thread2) thread2.model = previous;
            break;
          }
        }
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
      var previousModelValue = modelSelect.value;
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
        var selected = modelSelect.options[modelSelect.selectedIndex];
        if (selected && selected.dataset.loaded === 'false') {
          var prior = previousModelValue;
          var id = modelSelect.value;
          loadConfirmText.textContent = 'Start ' + id + '? Uses significant RAM. ' + statusRam.textContent;
          loadConfirmModal.hidden = false;
          pollStatus();
          loadCancelBtn.onclick = function () {
            loadConfirmModal.hidden = true;
            modelSelect.value = prior;
            pollStatus();
          };
          loadConfirmBtn.onclick = function () {
            loadConfirmModal.hidden = true;
            modelSelect.disabled = true;
            var opt = modelSelect.options[modelSelect.selectedIndex];
            var baseText = opt.value;
            var interval = setInterval(function () {
              var current = opt.textContent;
              if (current.indexOf('\ud83d\udfe2 ') === 0) {
                opt.textContent = '\u25cb ' + baseText;
              } else {
                opt.textContent = '\ud83d\udfe2 ' + baseText;
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

      // Initial load
      fetch('/api/v1/threads')
        .then(function (response) { return response.json(); })
        .then(function (data) {
          if (data.threads && data.threads.length > 0) {
            TC.threads = data.threads;
            TC.threadCounter = 0;
            for (var i = 0; i < TC.threads.length; i++) {
              if (TC.threads[i].id > TC.threadCounter) TC.threadCounter = TC.threads[i].id;
            }
            TC.activeThreadId = TC.threads[0].id;
            Threads.renderThreadMessages(TC.threads[0]);
            Threads.restoreThreadModelState(TC.threads[0]);
            Threads.renderSidebar();
          } else {
            Threads.createThread();
          }
        })
        .catch(function () {
          Threads.createThread();
        });
      fetchModels();
      input.focus();
    })();
