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
      var modelSelect = document.getElementById('model-select');
      var loadNemotronBtn = document.getElementById('load-nemotron');
      var unloadNemotronBtn = document.getElementById('unload-nemotron');
      var newThreadBtn = document.getElementById('new-thread-btn');
      var themeToggle = document.getElementById('theme-toggle');

      var THEMES = ['light', 'dark', 'matrix', 'phosphor', 'midnight', 'neon', 'crisp', 'ember', 'graphite-amber', 'graphite-forest'];
      var THEME_ICONS = { light: '☀️', dark: '🌙', matrix: '💊', phosphor: '>_ ', midnight: '🌃', neon: '⚡', crisp: '🌤', ember: '🔥', 'graphite-amber': '🔶', 'graphite-forest': '🌲' };

      function applyTheme(theme) {
        if (THEMES.indexOf(theme) === -1) theme = 'light';
        document.documentElement.setAttribute('data-theme', theme);
        if (theme === 'matrix' || theme === 'phosphor') {
          if (typeof window.MatrixRain !== 'undefined') { window.MatrixRain.start(); }
        } else {
          if (typeof window.MatrixRain !== 'undefined') { window.MatrixRain.stop(); }
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
          document.exitFullscreen().catch(function () {});
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
        try { console.warn('fullscreen failed:', info); } catch (e) {}
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
        statusModel.textContent = '● ' + (modelSelect.value || 'no model');
        statusModel.classList.toggle('ok', !!modelSelect.value);
        fetch('/api/v1/status')
          .then(function (r) { return r.json(); })
          .then(function (d) {
            var ram = 'RAM ' + d.ram_used_gb + '/' + d.ram_total_gb + ' GB';
            if (d.nemotron_loaded && d.nemotron_rss_gb) {
              ram += ' · nemotron ' + d.nemotron_rss_gb + ' GB';
            }
            statusRam.textContent = ram;
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
        TC.streaming = true;
        TC.currentController = new AbortController();
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

            if (eventType === 'token') {
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
              currentThread.messages.push({ role: 'assistant', content: replyText, ts: now, model: modelSelect.value || '' });
              renderReply(replyBubble, replyText);
              Threads.addBubbleChrome(replyBubble, MD.stripThink(replyText), now, modelSelect.value || '', currentThread.messages.length - 1);
              Threads.maybeRetitle(currentThread);
              Threads.persistThreads();
            } else if (eventType === 'error') {
              streamEnded = true;
              if (!userStored) { currentThread.messages.push({ role: 'user', content: message }); userStored = true; Threads.persistThreads(); }
              replyBubble.className = 'chat-bubble error';
              try {
                var errData = JSON.parse(dataStr);
                replyBubble.textContent = errData.message || FALLBACK_REPLY;
              } catch (err) {
                replyBubble.textContent = dataStr || FALLBACK_REPLY;
              }
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

          Threads.lockSelector();
          return read();
        })
        .catch(function (err) {
          streamEnded = true;
          if (!userStored) { currentThread.messages.push({ role: 'user', content: message, ts: Date.now() / 1000 }); userStored = true; }
          if (err && err.name === 'AbortError') {
            var partial = MD.stripThink(replyText).replace(/^\s+|\s+$/g, '');
            if (partial) {
              currentThread.messages.push({ role: 'assistant', content: partial, ts: Date.now() / 1000, model: modelSelect.value || '' });
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
          TC.currentController = null;
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
          try { if (document.execCommand('copy')) flash(); } catch (err) {}
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
          try { if (document.execCommand('copy')) copied(); } catch (err) {}
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
        fetch('/api/v1/models')
          .then(function (response) {
            if (!response.ok) throw new Error('Failed to fetch models');
            return response.json();
          })
          .then(function (data) {
            var previous = modelSelect.value;
            modelSelect.innerHTML = '';
            var models = data.models || [];
            if (models.length === 0) {
              var opt = document.createElement('option');
              opt.value = '';
              opt.textContent = 'No models available';
              modelSelect.appendChild(opt);
              return;
            }
            for (var i = 0; i < models.length; i++) {
              var opt = document.createElement('option');
              var id = models[i].id || '';
              opt.value = id;
              opt.textContent = id;
              modelSelect.appendChild(opt);
            }
            var opts = modelSelect.options;
            for (var j = 0; j < opts.length; j++) {
              if (opts[j].value === previous) {
                modelSelect.value = previous;
                var thread2 = TC.threads.find(function (t) { return t.id === TC.activeThreadId; });
                if (thread2) thread2.model = previous;
                break;
              }
            }
          })
          .catch(function () {
            modelSelect.innerHTML = '<option value="">Failed to load models</option>';
          });
      }

      function refreshModels() {
        fetchModels();
      }

      loadNemotronBtn.addEventListener('click', function () {
        loadNemotronBtn.disabled = true;
        fetch('/api/v1/nemotron/load', { method: 'POST' })
          .then(function (response) {
            if (!response.ok) throw new Error('Failed to load Nemotron');
            refreshModels();
          })
          .catch(function () {
            appendBubble('Failed to load Nemotron', 'error');
          })
          .finally(function () {
            loadNemotronBtn.disabled = false;
            pollStatus();
          });
      });

      unloadNemotronBtn.addEventListener('click', function () {
        unloadNemotronBtn.disabled = true;
        fetch('/api/v1/nemotron/unload', { method: 'POST' })
          .then(function (response) {
            if (!response.ok) throw new Error('Failed to unload Nemotron');
            refreshModels();
          })
          .catch(function () {
            appendBubble('Failed to unload Nemotron', 'error');
          })
          .finally(function () {
            unloadNemotronBtn.disabled = false;
            pollStatus();
          });
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
      modelSelect.addEventListener('change', function () {
        var thread = TC.threads.find(function (t) { return t.id === TC.activeThreadId; });
        if (thread) thread.model = modelSelect.value;
        pollStatus();
      });

      fetchModels();
      input.focus();
    })();
