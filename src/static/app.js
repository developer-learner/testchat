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

      var THEMES = ['light', 'dark', 'matrix'];
      var THEME_ICONS = { light: '☀️', dark: '🌙', matrix: '💊' };

      function applyTheme(theme) {
        if (THEMES.indexOf(theme) === -1) theme = 'light';
        document.documentElement.setAttribute('data-theme', theme);
        themeToggle.textContent = THEME_ICONS[theme];
        try { localStorage.setItem('testchat-theme', theme); } catch (e) { /* private mode */ }
      }

      themeToggle.addEventListener('click', function () {
        var current = document.documentElement.getAttribute('data-theme') || 'light';
        applyTheme(THEMES[(THEMES.indexOf(current) + 1) % THEMES.length]);
      });

      try { applyTheme(localStorage.getItem('testchat-theme') || 'light'); } catch (e) { applyTheme('light'); }

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
          container.appendChild(bubble);
        }
        scrollToBottom();
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
            var delBtn = document.createElement('button');
            delBtn.type = 'button';
            delBtn.className = 't-act t-del';
            delBtn.title = 'Delete';
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
      }

      function scrollToBottom() {
        container.scrollTop = container.scrollHeight;
      }

      function renderReply(bubble, text) {
        var html = renderThink(text);
        var visible = html.replace(/<span class=\"think-content\"[^>]*>[\s\S]*?<\/span>/g, '').replace(/<[^>]+>/g, '').trim();
        bubble.innerHTML = visible === '' ? 'thinking...' : html;
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
              var lm = lines[i].match(/^(\s*)([-*+]|\d+[.)])\s+(.*)$/);
              if (!lm) break;
              items.push({ lvl: lm[1].length >= 2 ? 1 : 0, ord: /\d/.test(lm[2].charAt(0)), text: lm[3] });
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
          out += '<li>' + renderMarkdownInline(it.text) + '</li>';
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

        appendBubble(message, 'user');
        input.value = '';
        streaming = true;
        currentController = new AbortController();
        sendBtn.type = 'button';
        sendBtn.textContent = 'Stop';
        sendBtn.classList.add('stop');

        var replyBubble = document.createElement('div');
        replyBubble.className = 'chat-bubble reply';
        replyBubble.setAttribute('data-testid', 'msg-assistant');
        container.appendChild(replyBubble);
        replyBubble.textContent = 'thinking...';
        replyText = '';
        var userStored = false;

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
              renderReply(replyBubble, replyText);
              scrollToBottom();
            } else if (eventType === 'think') {
              try {
                var parsed = JSON.parse(dataStr);
                replyText += '<think>' + parsed.content + '</think>';
              } catch (err) {
                replyText += '<think>' + dataStr + '</think>';
              }
              renderReply(replyBubble, replyText);
              scrollToBottom();
            } else if (eventType === 'done') {
              userStored = true;
              currentThread.messages.push({ role: 'user', content: message });
              currentThread.messages.push({ role: 'assistant', content: stripThink(replyText) });
              maybeRetitle(currentThread);
              persistThreads();
            } else if (eventType === 'error') {
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
          if (!userStored) { currentThread.messages.push({ role: 'user', content: message }); userStored = true; }
          if (err && err.name === 'AbortError') {
            // user hit Stop: keep the partial answer if any visible text
            // arrived, otherwise just drop the placeholder bubble
            var partial = stripThink(replyText).replace(/^\s+|\s+$/g, '');
            if (partial) {
              currentThread.messages.push({ role: 'assistant', content: partial });
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
          input.focus();
        });
      });

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
      });

      fetchModels();
      input.focus();
    })();
  
