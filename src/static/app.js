    (function () {
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
      var threadListEl = document.getElementById('thread-list');
      var themeToggle = document.getElementById('theme-toggle');

      var THEMES = ['light', 'dark', 'matrix', 'phosphor', 'midnight', 'neon', 'crisp', 'ember', 'graphite-amber', 'graphite-forest'];
      var THEME_ICONS = { light: '☀️', dark: '🌙', matrix: '💊', phosphor: '>_ ', midnight: '🌃', neon: '⚡', crisp: '🌤', ember: '🔥', 'graphite-amber': '🔶', 'graphite-forest': '🌲' };

      function applyTheme(theme) {
        if (THEMES.indexOf(theme) === -1) theme = 'light';
        document.documentElement.setAttribute('data-theme', theme);
        if (theme === 'phosphor') {
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

      // Focus mode: the zen class (chrome hidden) never depends on the
      // Fullscreen API succeeding — requestFullscreen needs a real user
      // gesture and can be denied outright in embedded contexts. Browser
      // fullscreen is best-effort on top; fullscreenchange keeps the two
      // in sync when Escape exits fullscreen natively.
      var fullscreenToggle = document.getElementById('fullscreen-toggle');

      function exitZen() {
        document.body.classList.remove('zen');
        if (document.fullscreenElement && document.exitFullscreen) {
          document.exitFullscreen().catch(function () {});
        }
      }

      fullscreenToggle.addEventListener('click', function () {
        document.body.classList.add('zen');
        if (document.documentElement.requestFullscreen) {
          document.documentElement.requestFullscreen().catch(function () {});
        }
      });

      document.addEventListener('fullscreenchange', function () {
        if (!document.fullscreenElement) document.body.classList.remove('zen');
      });

      var showThinking = false;
      var replyText = '';

      var threads = [];
      var activeThreadId = null;
      var threadCounter = 0;

      function saveThreadModelState() {
        var thread = threads.find(function (t) { return t.id === activeThreadId; });
        if (thread) {
          thread.model = modelSelect.value;
          thread.locked = modelSelect.disabled;
        }
      }

      function restoreThreadModelState(thread) {
        modelSelect.value = thread.model || '';
        modelSelect.disabled = !!thread.locked;
      }

      function persistThreads() {
        fetch('/api/v1/threads', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ threads: threads.map(function (t) { return { id: t.id, title: t.title, messages: t.messages, model: t.model || '', locked: !!t.locked }; }) })
        }).catch(function () {});
      }

      function createThread() {
        threadCounter++;
        var thread = {
          id: threadCounter,
          title: 'New Chat',
          messages: [],
          model: modelSelect.value,
          locked: false
        };
        threads.push(thread);
        activeThreadId = thread.id;
        container.innerHTML = '';
        container.classList.toggle('show-thinking', showThinking);
        modelSelect.disabled = false;
        renderSidebar();
        input.focus();
        persistThreads();
      }

      function switchThread(id) {
        saveThreadModelState();
        activeThreadId = id;
        container.innerHTML = '';
        container.classList.toggle('show-thinking', showThinking);
        var thread = threads.find(function (t) { return t.id === id; });
        if (thread) {
          renderThreadMessages(thread);
          restoreThreadModelState(thread);
        }
        renderSidebar();
      }

      function updateTitle(thread, firstMessage) {
        var title = firstMessage.trim();
        if (title.length > 30) {
          title = title.substring(0, 30) + '...';
        }
        thread.title = title;
        renderSidebar();
      }

      // meta line and hover actions ride on data-attributes + CSS pseudo
      // content so they never leak into the bubble's textContent
      function addBubbleChrome(bubble, raw, ts, model, idx) {
        bubble.dataset.raw = raw;
        var metaText = '';
        if (ts) {
          var d = new Date(ts * 1000);
          metaText = ('0' + d.getHours()).slice(-2) + ':' + ('0' + d.getMinutes()).slice(-2);
        }
        if (model) metaText += (metaText ? ' · ' : '') + model;
        if (metaText) {
          var meta = document.createElement('span');
          meta.className = 'bubble-meta';
          meta.setAttribute('data-meta', metaText);
          bubble.appendChild(meta);
        }
        var actions = document.createElement('span');
        actions.className = 'bubble-actions';
        var copyBtn = document.createElement('button');
        copyBtn.type = 'button';
        copyBtn.className = 'b-act b-copy';
        copyBtn.title = 'Copy message';
        actions.appendChild(copyBtn);
        if (typeof idx === 'number') {
          var delBtn = document.createElement('button');
          delBtn.type = 'button';
          delBtn.className = 'b-act b-del';
          delBtn.title = 'Delete message';
          delBtn.setAttribute('data-idx', String(idx));
          actions.appendChild(delBtn);
        }
        bubble.appendChild(actions);
      }

      function renderThreadMessages(thread) {
        for (var i = 0; i < thread.messages.length; i++) {
          var msg = thread.messages[i];
          var bubble = document.createElement('div');
          bubble.className = 'chat-bubble ' + (msg.role === 'user' ? 'user' : 'reply');
          bubble.setAttribute('data-testid', msg.role === 'user' ? 'msg-user' : 'msg-assistant');
          if (msg.role === 'assistant') {
            bubble.innerHTML = renderThink(msg.content);
          } else {
            bubble.textContent = msg.content;
          }
          addBubbleChrome(bubble, msg.content, msg.ts || 0, msg.role === 'assistant' ? (msg.model || '') : '', i);
          container.appendChild(bubble);
        }
        scrollToBottom();
      }

      function deleteMessagePair(idx) {
        var thread = threads.find(function (t) { return t.id === activeThreadId; });
        if (!thread || idx < 0 || idx >= thread.messages.length) return;
        if (!window.confirm('Delete this message' + (pairSpan(thread, idx) === 2 ? ' pair' : '') + '?')) return;
        var span = pairSpan(thread, idx);
        var start = idx;
        if (span === 2 && thread.messages[idx].role === 'assistant') start = idx - 1;
        thread.messages.splice(start, span);
        persistThreads();
        container.innerHTML = '';
        container.classList.toggle('show-thinking', showThinking);
        renderThreadMessages(thread);
      }

      function pairSpan(thread, idx) {
        var msg = thread.messages[idx];
        if (msg.role === 'user' && idx + 1 < thread.messages.length && thread.messages[idx + 1].role === 'assistant') return 2;
        if (msg.role === 'assistant' && idx > 0 && thread.messages[idx - 1].role === 'user') return 2;
        return 1;
      }

      function renderSidebar() {
        threadListEl.innerHTML = '';
        for (var i = 0; i < threads.length; i++) {
          (function (thread) {
            var item = document.createElement('div');
            item.className = 'thread-item' + (thread.id === activeThreadId ? ' active' : '');
            item.setAttribute('data-testid', 'thread-item');

            var title = document.createElement('span');
            title.className = 'thread-title';
            title.textContent = thread.title;
            item.appendChild(title);

            var actions = document.createElement('span');
            actions.className = 'thread-actions';
            var renBtn = document.createElement('button');
            renBtn.type = 'button';
            renBtn.className = 't-act t-ren';
            renBtn.title = 'Rename';
            renBtn.setAttribute('data-testid', 'thread-rename-btn');
            var delBtn = document.createElement('button');
            delBtn.type = 'button';
            delBtn.className = 't-act t-del';
            delBtn.title = 'Delete';
            delBtn.setAttribute('data-testid', 'thread-delete-btn');
            actions.appendChild(renBtn);
            actions.appendChild(delBtn);
            item.appendChild(actions);

            item.addEventListener('click', function () { switchThread(thread.id); });
            renBtn.addEventListener('click', function (e) {
              e.stopPropagation();
              startRename(thread, title, item);
            });
            delBtn.addEventListener('click', function (e) {
              e.stopPropagation();
              deleteThread(thread.id);
            });

            threadListEl.appendChild(item);
          })(threads[i]);
        }
      }

      function startRename(thread, titleEl, itemEl) {
        var inp = document.createElement('input');
        inp.className = 'thread-rename';
        inp.setAttribute('data-testid', 'thread-rename-input');
        inp.value = thread.title;
        itemEl.replaceChild(inp, titleEl);
        inp.focus();
        inp.select();
        var done = false;
        function commit() {
          if (done) return;
          done = true;
          var v = inp.value.trim();
          if (v) {
            thread.title = v;
            persistThreads();
          }
          renderSidebar();
        }
        inp.addEventListener('click', function (e) { e.stopPropagation(); });
        inp.addEventListener('keydown', function (e) {
          e.stopPropagation();
          if (e.key === 'Enter') commit();
          if (e.key === 'Escape') { done = true; renderSidebar(); }
        });
        inp.addEventListener('blur', commit);
      }

      function deleteThread(id) {
        if (!window.confirm('Delete this chat?')) return;
        threads = threads.filter(function (t) { return t.id !== id; });
        persistThreads();
        if (activeThreadId === id) {
          if (threads.length) {
            switchThread(threads[0].id);
          } else {
            createThread();
          }
        } else {
          renderSidebar();
        }
      }

      // A title like "hi" says nothing once the reply exists — retitle
      // generic threads from the first line of the first assistant reply.
      function maybeRetitle(thread) {
        var generic = thread.title === 'New Chat' ||
          (/^(hi+|hello|hey|yo|sup|test)\b/i.test(thread.title) && thread.title.length <= 12);
        if (!generic) return;
        var reply = null;
        for (var i = 0; i < thread.messages.length; i++) {
          if (thread.messages[i].role === 'assistant') { reply = thread.messages[i]; break; }
        }
        if (!reply) return;
        var t = stripThink(reply.content).replace(/[#*`>_]/g, '').replace(/\s+/g, ' ').trim();
        if (t.length > 30) t = t.substring(0, 30) + '...';
        if (t) {
          thread.title = t;
          renderSidebar();
        }
      }

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
        var html = renderThink(text);
        var visible = html.replace(/<span class=\"think-content\"[^>]*>[\s\S]*?<\/span>/g, '').replace(/<[^>]+>/g, '').trim();
        bubble.innerHTML = visible === '' ? 'thinking...' : html;
        bubble.dataset.raw = stripThink(text);
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

      function renderThink(text) {
        // streaming wraps each think chunk in its own tag pair; merge
        // adjacent blocks so they render as one span, not one per chunk
        text = text.replace(/<\/think>\s*<think>/g, '');
        var html = '';
        var inThink = false;
        var afterThink = false;
        var parts = text.split(/(<think>|<\/think>)/);
        for (var i = 0; i < parts.length; i++) {
          var part = parts[i];
          if (part === '<think>') { inThink = true; continue; }
          if (part === '</think>') { inThink = false; afterThink = true; continue; }
          var escaped = part.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
          if (inThink) {
            html += '<span class="think-content" data-testid="think-content">' + escaped.replace(/^\s+|\s+$/g, '') + '</span>';
          } else {
            var visiblePart = escaped.replace(/^\s+|\s+$/g, '');
            if (visiblePart !== '') {
              html += '<div class="md">' + renderMarkdownBlocks(visiblePart) + '</div>';
            }
            afterThink = false;
          }
        }
        return html;
      }

      // Inline markdown for already-HTML-escaped text.
      function renderMarkdownInline(escaped) {
        return escaped
          .replace(/`([^`\n]+)`/g, '<code>$1</code>')
          .replace(/\*\*([^*\n][^*]*?)\*\*/g, '<strong>$1</strong>')
          .replace(/(^|[\s(])\*([^*\s][^*\n]*?)\*(?=[\s.,;:!?)]|$)/g, '$1<em>$2</em>')
          .replace(/\[([^\]]+)\]\((https?:[^)\s"]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
      }

      // Block-level markdown for already-HTML-escaped text: fenced code
      // (with copy button), headings, ul/ol (one nesting level), block
      // quotes, hr, paragraphs. Single newlines inside a paragraph become
      // <br> so the model's line intent is preserved without pre-wrap.
      function renderMarkdownBlocks(escaped) {
        var lines = escaped.split('\n');
        var out = '';
        var para = [];
        var i, m;

        function flushPara() {
          if (para.length) {
            out += '<p>' + para.join('<br>') + '</p>';
            para = [];
          }
        }

        for (i = 0; i < lines.length; i++) {
          var line = lines[i];

          if (/^```/.test(line)) {
            flushPara();
            var code = [];
            i++;
            while (i < lines.length && !/^```/.test(lines[i])) { code.push(lines[i]); i++; }
            out += '<div class="code-block"><button type="button" class="copy-btn">copy</button><pre><code>' + code.join('\n') + '</code></pre></div>';
            continue;
          }

          m = line.match(/^(#{1,6})\s+(.*)$/);
          if (m) {
            flushPara();
            out += '<div class="md-h md-h' + m[1].length + '">' + renderMarkdownInline(m[2]) + '</div>';
            continue;
          }

          if (/^\s*([-*_])\s*\1\s*\1[\s\-*_]*$/.test(line)) {
            flushPara();
            out += '<hr>';
            continue;
          }

          if (/^&gt;\s?/.test(line)) {
            flushPara();
            var quote = [];
            while (i < lines.length && /^&gt;\s?/.test(lines[i])) {
              quote.push(renderMarkdownInline(lines[i].replace(/^&gt;\s?/, '')));
              i++;
            }
            i--;
            out += '<blockquote>' + quote.join('<br>') + '</blockquote>';
            continue;
          }

          m = line.match(/^(\s*)([-*+]|\d+[.)])\s+(.*)$/);
          if (m) {
            flushPara();
            var items = [];
            while (i < lines.length) {
              // models often blank-line-separate list items; a lone blank
              // followed by another item is still the same list
              if (lines[i].trim() === '' && i + 1 < lines.length &&
                  /^(\s*)([-*+]|\d+[.)])\s+/.test(lines[i + 1])) {
                i++;
                continue;
              }
              var lm = lines[i].match(/^(\s*)([-*+]|\d+[.)])\s+(.*)$/);
              if (!lm) break;
              items.push({
                lvl: lm[1].length >= 2 ? 1 : 0,
                ord: /\d/.test(lm[2].charAt(0)),
                num: parseInt(lm[2], 10) || 0,
                text: lm[3]
              });
              i++;
            }
            i--;
            out += renderListItems(items);
            continue;
          }

          if (line.trim() === '') {
            flushPara();
            continue;
          }
          para.push(renderMarkdownInline(line));
        }
        flushPara();
        return out;
      }

      function renderListItems(items) {
        var out = '';
        var open = [];
        for (var k = 0; k < items.length; k++) {
          var it = items[k];
          var tag = it.ord ? 'ol' : 'ul';
          var depth = it.lvl + 1;
          while (open.length > depth) { out += '</' + open.pop() + '>'; }
          if (open.length === depth && open[open.length - 1] !== tag && it.lvl === 0) {
            out += '</' + open.pop() + '>';
          }
          while (open.length < depth) { out += '<' + tag + '>'; open.push(tag); }
          // carry the source numbering so lists render exactly as written
          // (loose lists, restarts, lists starting past 1)
          out += (it.ord && it.num ? '<li value="' + it.num + '">' : '<li>') + renderMarkdownInline(it.text) + '</li>';
        }
        while (open.length) { out += '</' + open.pop() + '>'; }
        return out;
      }

      function stripThink(text) {
        var OPEN_TAG = '<' + 'think>';
        var CLOSE_TAG = '</' + 'think>';
        var escapedOpen = OPEN_TAG.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        var escapedClose = CLOSE_TAG.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        var pattern = escapedOpen + '.*?' + escapedClose;
        text = text.replace(new RegExp(pattern, 'gs'), '');
        var pattern2 = escapedOpen + '.+$';
        text = text.replace(new RegExp(pattern2, 's'), '');
        return text;
      }

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
                var thread2 = threads.find(function (t) { return t.id === activeThreadId; });
                if (thread2) thread2.model = previous;
                break;
              }
            }
          })
          .catch(function () {
            modelSelect.innerHTML = '<option value="">Failed to load models</option>';
          });
      }

      function lockSelector() {
        var thread = threads.find(function (t) { return t.id === activeThreadId; });
        if (thread && !thread.locked) {
          thread.locked = true;
          modelSelect.disabled = true;
        }
      }

      var streaming = false;
      var currentController = null;
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

      sendBtn.addEventListener('click', function () {
        if (streaming && currentController) currentController.abort();
      });

      form.addEventListener('submit', function (e) {
        e.preventDefault();
        if (streaming) return;
        var message = input.value.trim();
        if (!message) return;

        var currentThread = threads.find(function (t) { return t.id === activeThreadId; });

        if (currentThread.messages.length === 0) {
          updateTitle(currentThread, message);
        }

        var userBubble = appendBubble(message, 'user');
        addBubbleChrome(userBubble, message, Date.now() / 1000, '');
        input.value = '';
        streaming = true;
        currentController = new AbortController();
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

        // re-rendering the full markdown on every token is O(reply length);
        // coalesce to one render per 30ms so long replies stream smoothly
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

        var bodyObj = { message: message, history: currentThread.messages };
        if (modelSelect.value) {
          bodyObj.model = modelSelect.value;
        }

        fetch('/api/v1/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(bodyObj),
          signal: currentController.signal
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
              currentThread.messages.push({ role: 'assistant', content: stripThink(replyText), ts: now, model: modelSelect.value || '' });
              renderReply(replyBubble, replyText);
              addBubbleChrome(replyBubble, stripThink(replyText), now, modelSelect.value || '', currentThread.messages.length - 1);
              maybeRetitle(currentThread);
              persistThreads();
            } else if (eventType === 'error') {
              streamEnded = true;
              if (!userStored) { currentThread.messages.push({ role: 'user', content: message }); userStored = true; persistThreads(); }
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

          lockSelector();
          return read();
        })
        .catch(function (err) {
          streamEnded = true;
          if (!userStored) { currentThread.messages.push({ role: 'user', content: message, ts: Date.now() / 1000 }); userStored = true; }
          if (err && err.name === 'AbortError') {
            // user hit Stop: keep the partial answer if any visible text
            // arrived, otherwise just drop the placeholder bubble
            var partial = stripThink(replyText).replace(/^\s+|\s+$/g, '');
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
          persistThreads();
        })
        .finally(function () {
          streaming = false;
          currentController = null;
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

      // per-message hover actions (event delegation)
      container.addEventListener('click', function (e) {
        var btn = e.target;
        if (!btn.classList) return;
        if (btn.classList.contains('b-copy')) {
          copyToClipboard(btn.closest('.chat-bubble').dataset.raw || '', btn);
        } else if (btn.classList.contains('b-del')) {
          deleteMessagePair(parseInt(btn.getAttribute('data-idx'), 10));
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

      // copy button on fenced code blocks (event delegation — blocks are
      // re-rendered on every streamed chunk)
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
        showThinking = !showThinking;
        thinkToggle.classList.toggle('on');
        container.classList.toggle('show-thinking');
      });

      newThreadBtn.addEventListener('click', function () {
        createThread();
      });

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

      fetch('/api/v1/threads')
        .then(function (response) { return response.json(); })
        .then(function (data) {
          if (data.threads && data.threads.length > 0) {
            threads = data.threads;
            threadCounter = 0;
            for (var i = 0; i < threads.length; i++) {
              if (threads[i].id > threadCounter) threadCounter = threads[i].id;
            }
            activeThreadId = threads[0].id;
            renderThreadMessages(threads[0]);
            restoreThreadModelState(threads[0]);
            renderSidebar();
          } else {
            createThread();
          }
        })
        .catch(function () {
          createThread();
        });
      modelSelect.addEventListener('change', function () {
        var thread = threads.find(function (t) { return t.id === activeThreadId; });
        if (thread) thread.model = modelSelect.value;
        pollStatus();
      });

      fetchModels();
      input.focus();
    })();
  
