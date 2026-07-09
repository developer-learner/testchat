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
          if (msg.role === 'assistant') {
            bubble.setAttribute('data-testid', 'msg-assistant');
            bubble.innerHTML = renderThink(msg.content);
          } else {
            bubble.setAttribute('data-testid', 'msg-user');
            bubble.textContent = msg.content;
          }
          container.appendChild(bubble);
        }
        scrollToBottom();
      }

      function renderSidebar() {
        threadListEl.innerHTML = '';
        for (var i = 0; i < threads.length; i++) {
          var thread = threads[i];
          var item = document.createElement('div');
          item.className = 'thread-item' + (thread.id === activeThreadId ? ' active' : '');
          item.setAttribute('data-testid', 'thread-item');
          item.textContent = thread.title;
          (function (tid) {
            item.addEventListener('click', function () { switchThread(tid); });
          })(thread.id);
          threadListEl.appendChild(item);
        }
      }

      function appendBubble(text, type) {
        var bubble = document.createElement('div');
        bubble.className = 'chat-bubble ' + type;
        if (type === 'user') {
          bubble.setAttribute('data-testid', 'msg-user');
        }
        bubble.textContent = text;
        container.appendChild(bubble);
        scrollToBottom();
      }

      function scrollToBottom() {
        container.scrollTop = container.scrollHeight;
      }

      function renderThink(text) {
        var html = '';
        var inThink = false;
        var parts = text.split(/(') { inThink = false; continue; }
          var escaped = part.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
          html += inThink ? '<span class="think-content" data-testid="think-content">' + escaped + '</span>' : escaped;
        }
        return html;
      }

      function stripThink(text) {
        return text.replace(/';
              } catch (err) {
                replyText += '';
              }
              replyBubble.innerHTML = renderThink(replyText);
              scrollToBottom();
            } else if (eventType === 'done') {
              currentThread.messages.push({ role: 'user', content: message });
              currentThread.messages.push({ role: 'assistant', content: stripThink(replyText) });
            } else if (eventType === 'error') {
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
        .catch(function () {
          replyBubble.className = 'chat-bubble error';
          replyBubble.textContent = FALLBACK_REPLY;
        })
        .finally(function () {
          sendBtn.disabled = false;
          input.focus();
        });
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

      createThread();
      modelSelect.addEventListener('change', function () {
        var thread = threads.find(function (t) { return t.id === activeThreadId; });
        if (thread) thread.model = modelSelect.value;
      });

      fetchModels();
      input.focus();
    })();