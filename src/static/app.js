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
      // The load-confirm modal is shared: catalog.js drives it for the
      // change-handler flow; app.js drives it here for the "Send with
      // unloaded model → offer load, then auto-resubmit" flow. Both paths
      // reassign loadCancelBtn.onclick / loadConfirmBtn.onclick; latest
      // write wins, which is fine because only one flow runs at a time.
      var loadConfirmModal = document.getElementById('load-confirm-modal');
      var loadConfirmBtn = document.getElementById('load-confirm');
      var loadCancelBtn = document.getElementById('load-cancel');
      var loadConfirmText = document.getElementById('load-confirm-text');
      var newThreadBtn = document.getElementById('new-thread-btn');

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

      // Bubble helpers
      function appendBubble(text, type) {
        var bubble = document.createElement('div');
        bubble.className = 'chat-bubble ' + type;
        bubble.textContent = text;
        bubble.setAttribute('data-testid',
          type === 'user' ? 'msg-user' : type === 'error' ? 'msg-error' : 'msg-assistant');
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

      // Ctrl/Cmd+Enter submits; plain Enter and Shift+Enter keep the default
      // newline behavior. Also auto-grow the textarea up to ~40vh so a
      // multi-line paste (markdown blocks, code) is readable without hiding
      // the messages behind a scrolling wall.
      function autogrow() {
        input.style.height = 'auto';
        var cap = Math.round(window.innerHeight * 0.4);
        input.style.height = Math.min(input.scrollHeight, cap) + 'px';
      }
      input.addEventListener('input', autogrow);
      input.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey) && !e.isComposing) {
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

        // No model chosen (fresh chat, nothing loaded): don't hit /api/v1/chat
        // with an unset model — the server would return a bare 422 the UI has
        // no handler for. Focus the selector so the fix is one keystroke away.
        if (!modelSelect.value) {
          appendBubble('Pick a model from the dropdown before sending.', 'error');
          modelSelect.focus();
          return;
        }
        // Selected model is unloaded. Historically this was reachable only via
        // the change event, so re-picking the already-shown option was a dead
        // end; Send now offers the same load modal and auto-resubmits when the
        // load returns 200, so the user's one Send click is enough.
        var sel = modelSelect.options[modelSelect.selectedIndex];
        if (sel && sel.dataset.loaded === 'false' && !TC.modelLoading) {
          var loadId = modelSelect.value;
          loadConfirmText.textContent = 'Start ' + loadId + ' first, then send? Uses significant RAM. ' + statusRam.textContent;
          loadConfirmModal.hidden = false;
          loadCancelBtn.onclick = function () { loadConfirmModal.hidden = true; };
          loadConfirmBtn.onclick = function () {
            loadConfirmModal.hidden = true;
            TC.modelLoading = true;
            fetch('/api/v1/script-models/' + encodeURIComponent(loadId) + '/load', { method: 'POST' })
              .then(function (r) {
                if (!r.ok) throw new Error('Failed to load model');
                // Refresh in the background so the option list re-syncs; flip
                // this option's data-loaded inline so the resubmit's guard
                // (which reads the DOM, not the server) lets it through.
                sel.dataset.loaded = 'true';
                sel.textContent = '🟢 ' + loadId;
                window.Catalog.refreshModels();
                form.dispatchEvent(new Event('submit', { cancelable: true }));
              })
              .catch(function (err) { appendBubble(err.message || 'Failed to load model', 'error'); })
              .finally(function () { TC.modelLoading = false; });
          };
          return;
        }

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
                var errAssistant = { role: 'assistant', content: errPartial, ts: errNow, model: streamModel || '' };
                if (pendingSources.length) {
                  errAssistant.sources = pendingSources.map(function (s) { return { title: s.title, url: s.url }; });
                }
                currentThread.messages.push(errAssistant);
                renderReply(replyBubble, replyText);
                Threads.addBubbleChrome(replyBubble, errPartial, errNow, streamModel || '', currentThread.messages.length - 1);
                if (pendingSources.length || pendingNotice) {
                  setTimeout(function () { Threads.addSources(replyBubble, pendingSources, pendingNotice); }, 0);
                }
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
          // A rejection can land AFTER the final SSE frame was processed
          // (Stop clicked as done arrives, or unclean connection teardown
          // right behind the last frame). Everything is stored and rendered
          // by then — pushing again would duplicate the reply in history.
          if (streamEnded) return;
          streamEnded = true;
          if (!userStored) { currentThread.messages.push({ role: 'user', content: message, ts: Date.now() / 1000 }); userStored = true; }
          var caughtPartial = MD.stripThink(replyText).replace(/^\s+|\s+$/g, '');
          var isAbort = err && err.name === 'AbortError';
          if (caughtPartial) {
            // Any post-token failure (stop button OR connection drop) keeps
            // the partial reply and its sources; only the abort path stays
            // silent about the error, the network case surfaces a bubble.
            var caughtNow = Date.now() / 1000;
            var caughtMsg = { role: 'assistant', content: caughtPartial, ts: caughtNow, model: streamModel || '' };
            if (pendingSources.length) {
              caughtMsg.sources = pendingSources.map(function (s) { return { title: s.title, url: s.url }; });
            }
            currentThread.messages.push(caughtMsg);
            renderReply(replyBubble, replyText);
            Threads.addBubbleChrome(replyBubble, caughtPartial, caughtNow, streamModel || '', currentThread.messages.length - 1);
            if (pendingSources.length || pendingNotice) {
              setTimeout(function () { Threads.addSources(replyBubble, pendingSources, pendingNotice); }, 0);
            }
            if (!isAbort && replyBubble.parentNode) appendBubble(FALLBACK_REPLY, 'error');
          } else if (isAbort) {
            if (replyBubble.parentNode) replyBubble.parentNode.removeChild(replyBubble);
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

      // Exposed for chrome.js (fsDiag error) and catalog.js (load/unload
      // error paths, plus pollStatus after unload / around a load confirm).
      window.App = {
        appendBubble: appendBubble,
        pollStatus: pollStatus
      };

      // Initial load — retry loop until GET /api/v1/threads succeeds
      (function retryInitialLoad() {
        // At the START of every iteration, BEFORE issuing the fetch, write the
        // warning text to the history-status element. This re-asserts the
        // warning on every retry even if something else overwrites the element
        // in between (a standalone script-eval GET in threads.js that backs the
        // load-path quarantine indicator races this code and overwrites the
        // element with "" when no quarantine is present — the re-assert on the
        // next retry tick is what keeps the warning visible while hydration
        // keeps failing).
        var historyStatus = document.querySelector('[data-testid="history-status"]');
        if (historyStatus) historyStatus.textContent = 'history unavailable — retrying';

        fetch('/api/v1/threads')
          .then(function (response) {
            if (!response.ok) throw new Error('non-ok status');
            return response.json();
          })
          .then(function (data) {
            // On success: set the history-status text to the single-owner value
            // driven by the hydration response — the ONLY source for this element.
            if (historyStatus) historyStatus.textContent = data.quarantined ? 'history unreadable (backup kept)' : '';
            // ERD-DELTA v73: hydrate the persistence owner with the server's
            // revision BEFORE any mutation can enqueue (createThread calls
            // persistThreads, which enqueues a PUT that reads _hydratedRevision).
            Threads.setHydratedRevision(data.revision != null ? data.revision : 0);
            if (data.threads && data.threads.length > 0) {
              TC.threads = data.threads;
              TC.threadCounter = 0;
              for (var i = 0; i < TC.threads.length; i++) {
                if (TC.threads[i].id > TC.threadCounter) TC.threadCounter = TC.threads[i].id;
              }
              // AC-123: open the NEWEST thread — the one the sidebar renders at
              // the top. threads[] is oldest-first, so that is the last element,
              // not the first. No last-opened pin is restored.
              var newest = TC.threads[TC.threads.length - 1];
              TC.activeThreadId = newest.id;
              Threads.renderThreadMessages(newest);
              Threads.restoreThreadModelState(newest);
              Threads.renderSidebar();
            } else {
              Threads.createThread();
            }
          })
          .catch(function () {
            // On failure: the warning text was already written at the top of
            // this iteration. Do NOT call Threads.createThread() on failure —
            // revision is unknown, so creating replacement state could destroy
            // survivors. Schedule the next retry via a short setTimeout loop.
            setTimeout(retryInitialLoad, 1000);
          });
      })();
      window.Catalog.fetchModels();
      input.focus();
    })();
