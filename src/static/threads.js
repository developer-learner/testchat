window.TC = {
  threads: [],
  activeThreadId: null,
  threadCounter: 0,
  streaming: false,
  currentController: null,
  showThinking: false
};

let threadSearchQuery = '';

let hitElements = [];
let hitIndex = 0;

window.Threads = (function () {
  var TC = window.TC;

  function el(id) { return document.getElementById(id); }

  function persistThreads() {
    fetch('/api/v1/threads', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ threads: TC.threads.map(function (t) { return { id: t.id, title: t.title, messages: t.messages, model: t.model || '', locked: !!t.locked }; }) })
    }).catch(function () {});
  }

  function saveThreadModelState() {
    var thread = TC.threads.find(function (t) { return t.id === TC.activeThreadId; });
    if (thread) {
      thread.model = el('model-select').value;
      thread.locked = el('model-select').disabled;
    }
  }

  function restoreThreadModelState(thread) {
    el('model-select').value = thread.model || '';
    el('model-select').disabled = !!thread.locked;
  }

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
    var container = el('chat-container');
    for (var i = 0; i < thread.messages.length; i++) {
      var msg = thread.messages[i];
      var bubble = document.createElement('div');
      bubble.className = 'chat-bubble ' + (msg.role === 'user' ? 'user' : 'reply');
      bubble.setAttribute('data-testid', msg.role === 'user' ? 'msg-user' : 'msg-assistant');
      if (msg.role === 'assistant') {
        bubble.innerHTML = MD.renderThink(msg.content);
      } else {
        bubble.textContent = msg.content;
      }
      addBubbleChrome(bubble, msg.content, msg.ts || 0, msg.role === 'assistant' ? (msg.model || '') : '', i);
      container.appendChild(bubble);
    }
    container.scrollTop = container.scrollHeight;
  }

  function highlightSearchHits() {
    var container = el('chat-container');
    if (!threadSearchQuery) { hitElements = []; return; }
    var walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, null, false);
    var textNodes = [];
    var node;
    while ((node = walker.nextNode())) {
      textNodes.push(node);
    }
    var firstMark = null;
    for (var i = 0; i < textNodes.length; i++) {
      var tn = textNodes[i];
      if (!tn.parentNode) continue;
      var p = tn.parentNode;
      var insideMark = false;
      while (p && p !== container) {
        if (p.tagName === 'MARK') { insideMark = true; break; }
        p = p.parentNode;
      }
      if (insideMark) continue;
      var text = tn.textContent;
      var lowerText = text.toLowerCase();
      var query = threadSearchQuery;
      var idx = lowerText.indexOf(query);
      if (idx === -1) continue;
      var fragment = document.createDocumentFragment();
      var lastIndex = 0;
      while (idx !== -1) {
        if (idx > lastIndex) {
          fragment.appendChild(document.createTextNode(text.substring(lastIndex, idx)));
        }
        var mark = document.createElement('mark');
        mark.className = 'search-hit';
        mark.setAttribute('data-testid', 'search-hit');
        mark.textContent = text.substring(idx, idx + query.length);
        fragment.appendChild(mark);
        if (!firstMark) firstMark = mark;
        lastIndex = idx + query.length;
        idx = lowerText.indexOf(query, lastIndex);
      }
      if (lastIndex < text.length) {
        fragment.appendChild(document.createTextNode(text.substring(lastIndex)));
      }
      tn.parentNode.replaceChild(fragment, tn);
    }
    hitElements = document.querySelectorAll('mark.search-hit');
    hitIndex = 0;
    updateHitNav();
  }

  function updateHitNav() {
    var nav = document.querySelector('.search-hit-nav');
    if (!nav) return;
    if (hitElements.length === 0) { nav.hidden = true; return; }
    nav.hidden = false;
    var countSpan = document.querySelector('[data-testid="search-hit-count"]');
    if (countSpan) countSpan.textContent = hitElements.length ? (hitIndex + 1) + '/' + hitElements.length : '0/0';
    hitElements.forEach(el => el.classList.remove('current'));
    if (hitElements.length > 0) {
      hitElements[hitIndex].classList.add('current');
      hitElements[hitIndex].scrollIntoView({ block: 'center' });
    }
  }

  function gotoHit(delta) {
    if (hitElements.length === 0) return;
    hitIndex = (hitIndex + delta % hitElements.length + hitElements.length) % hitElements.length;
    updateHitNav();
  }

  function pairSpan(thread, idx) {
    var msg = thread.messages[idx];
    if (msg.role === 'user' && idx + 1 < thread.messages.length && thread.messages[idx + 1].role === 'assistant') return 2;
    if (msg.role === 'assistant' && idx > 0 && thread.messages[idx - 1].role === 'user') return 2;
    return 1;
  }

  function deleteMessagePair(idx) {
    var thread = TC.threads.find(function (t) { return t.id === TC.activeThreadId; });
    if (!thread || idx < 0 || idx >= thread.messages.length) return;
    if (!window.confirm('Delete this message' + (pairSpan(thread, idx) === 2 ? ' pair' : '') + '?')) return;
    var span = pairSpan(thread, idx);
    var start = idx;
    if (span === 2 && thread.messages[idx].role === 'assistant') start = idx - 1;
    thread.messages.splice(start, span);
    persistThreads();
    var container = el('chat-container');
    container.innerHTML = '';
    container.classList.toggle('show-thinking', TC.showThinking);
    renderThreadMessages(thread);
  }

  function renderSidebar() {
    var threadListEl = el('thread-list');
    threadListEl.innerHTML = '';
    for (var i = TC.threads.length - 1; i >= 0; i--) {
      (function (thread) {
        if (threadSearchQuery) {
          var titleMatch = thread.title.toLowerCase().includes(threadSearchQuery);
          var msgMatch = false;
          for (var m = 0; m < thread.messages.length; m++) {
            if (thread.messages[m].content.toLowerCase().includes(threadSearchQuery)) { msgMatch = true; break; }
          }
          if (!titleMatch && !msgMatch) return;
        }
        var item = document.createElement('div');
        item.className = 'thread-item' + (thread.id === TC.activeThreadId ? ' active' : '');
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
      })(TC.threads[i]);
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
    TC.threads = TC.threads.filter(function (t) { return t.id !== id; });
    persistThreads();
    if (TC.activeThreadId === id) {
      if (TC.threads.length) {
        switchThread(TC.threads[0].id);
      } else {
        createThread();
      }
    } else {
      renderSidebar();
    }
  }

  function updateTitle(thread, firstMessage) {
    var title = firstMessage.trim();
    if (title.length > 30) {
      title = title.substring(0, 30) + '...';
    }
    thread.title = title;
    renderSidebar();
  }

  function maybeRetitle(thread) {
    var generic = thread.title === 'New Chat' ||
      (/^(hi+|hello|hey|yo|sup|test)\b/i.test(thread.title) && thread.title.length <= 12);
    if (!generic) return;
    var reply = null;
    for (var i = 0; i < thread.messages.length; i++) {
      if (thread.messages[i].role === 'assistant') { reply = thread.messages[i]; break; }
    }
    if (!reply) return;
    var t = MD.stripThink(reply.content).replace(/[#*`>_]/g, '').replace(/\s+/g, ' ').trim();
    if (t.length > 30) t = t.substring(0, 30) + '...';
    if (t) {
      thread.title = t;
      renderSidebar();
    }
  }

  function createThread() {
    TC.threadCounter++;
    var modelSelect = el('model-select');
    var thread = {
      id: TC.threadCounter,
      title: 'New Chat',
      messages: [],
      model: modelSelect.value,
      locked: false
    };
    TC.threads.push(thread);
    TC.activeThreadId = thread.id;
    var container = el('chat-container');
    container.innerHTML = '';
    container.classList.toggle('show-thinking', TC.showThinking);
    modelSelect.disabled = false;
    renderSidebar();
    el('message-input').focus();
    persistThreads();
  }

  function switchThread(id) {
    saveThreadModelState();
    TC.activeThreadId = id;
    var container = el('chat-container');
    container.innerHTML = '';
    container.classList.toggle('show-thinking', TC.showThinking);
    var thread = TC.threads.find(function (t) { return t.id === id; });
    if (thread) {
      renderThreadMessages(thread);
      restoreThreadModelState(thread);
      highlightSearchHits();
    }
    renderSidebar();
  }

  if (document.getElementById('thread-search')) {
    document.getElementById('thread-search').addEventListener('input', function (e) {
      threadSearchQuery = e.target.value.toLowerCase().trim();
      renderSidebar();
      var container = el('chat-container');
      container.innerHTML = '';
      container.classList.toggle('show-thinking', TC.showThinking);
      var thread = TC.threads.find(function (t) { return t.id === TC.activeThreadId; });
      if (thread) {
        renderThreadMessages(thread);
      }
      highlightSearchHits();
    });
  }

  var prevBtn = document.querySelector('[data-testid="search-prev-btn"]');
  var nextBtn = document.querySelector('[data-testid="search-next-btn"]');
  if (prevBtn) prevBtn.addEventListener('click', function () { gotoHit(-1); });
  if (nextBtn) nextBtn.addEventListener('click', function () { gotoHit(1); });

  return {
    persistThreads: persistThreads,
    saveThreadModelState: saveThreadModelState,
    restoreThreadModelState: restoreThreadModelState,
    addBubbleChrome: addBubbleChrome,
    renderThreadMessages: renderThreadMessages,
    deleteMessagePair: deleteMessagePair,
    renderSidebar: renderSidebar,
    updateTitle: updateTitle,
    maybeRetitle: maybeRetitle,
    createThread: createThread,
    switchThread: switchThread,
    lockSelector: function () {
      var thread = TC.threads.find(function (t) { return t.id === TC.activeThreadId; });
      if (thread && !thread.locked) {
        thread.locked = true;
        el('model-select').disabled = true;
      }
    }
  };
})();
