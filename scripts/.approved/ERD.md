ERD — testchat M25: Web-Informed Answers (erd_version 46)

What changes v45 -> v46

One new backend service (websearch.py), anchored edits in three backend
files and three frontend files. Three frontend files remain no_edit_files
(D-65). The DAG below is the required order. One new external
(external:tavily-search, capture frozen with this spec). No new stack
imports — the Tavily client is urllib, matching llm.py's convention.

File inventory (M25 build) — DAG order

1. src/services/websearch.py — CREATE (~85 lines). Module docstring:
   "Tavily web search client (M25). Key from TAVILY_API_KEY; endpoint
   overridable via TAVILY_ENDPOINT for the sandboxed suite." Contents,
   in order:

   - imports: json, logging, os, urllib.error, urllib.request
   - module logger via logging.getLogger(__name__)
   - DEFAULT_ENDPOINT = "https://api.tavily.com/search"
   - MAX_SOURCES = 4
   - MAX_CONTENT_CHARS = 2000
   - class WebSearchError(Exception) with docstring "Any failure to
     obtain search results — caller falls back to an un-augmented call."
   - def is_configured() -> bool: returns bool(os.environ.get(
     "TAVILY_API_KEY", "").strip())
   - def search_web(query: str) -> list[dict]:
     raises WebSearchError if not is_configured().
     POSTs json {"query": query, "max_results": MAX_SOURCES} to
     os.environ.get("TAVILY_ENDPOINT", DEFAULT_ENDPOINT) with headers
     Content-Type: application/json and Authorization: Bearer <key>,
     timeout float(os.environ.get("TAVILY_TIMEOUT_SECONDS", "10")).
     Parses the response per captures/tavily-search.json: top-level
     "results" list; for each of the first MAX_SOURCES entries builds
     {"title": str(r.get("title", "")), "url": str(r.get("url", "")),
      "content": str(r.get("content", ""))[:MAX_CONTENT_CHARS]}.
     EVERY failure path (urllib.error.URLError, urllib.error.HTTPError,
     OSError, json.JSONDecodeError, KeyError, TypeError, ValueError)
     logs a warning and raises WebSearchError — never returns partial
     garbage.
   - def build_prompt(message: str, sources: list[dict]) -> str:
     returns the augmented prompt, exactly this structure:
     "Web search results (cite sources by number, like [1]):\n\n"
     then for each source i (1-based):
     "[{i}] {title}\n{url}\n{content}\n\n"
     then "Using the results above when relevant, answer:\n{message}"

2. src/api/status.py — EDIT (two anchored edits, one task; depends on 1).

   Edit A — the import block currently contains exactly:
   ```
   from src.services import models as models_service
   ```
   Replace with:
   ```
   from src.services import models as models_service
   from src.services import websearch
   ```

   Edit B — the get_status return currently contains exactly:
   ```
        "loadable_gb": round(_loadable_gb(), 1),
    }
   ```
   Replace with:
   ```
        "loadable_gb": round(_loadable_gb(), 1),
        "web_configured": websearch.is_configured(),
    }
   ```

3. src/api/chat.py — EDIT (three anchored edits, one task; depends on 1).

   Edit A — the import block currently contains exactly:
   ```
   import src.services.llm as llm_mod
   ```
   Replace with:
   ```
   import src.services.llm as llm_mod
   from src.services import websearch
   ```

   Edit B — ChatRequest currently reads exactly:
   ```
   class ChatRequest(BaseModel):
       message: str
       model: StrictStr | None = None
       history: list[HistoryEntry] = []
   ```
   Replace with:
   ```
   class ChatRequest(BaseModel):
       message: str
       model: StrictStr | None = None
       history: list[HistoryEntry] = []
       web: bool = False
   ```

   Edit C — the generator opening currently reads exactly:
   ```
    async def event_generator():
        history_dicts = [{"role": e.role, "content": e.content} for e in request.history]
        try:
            for item in llm_mod.stream_reply(request.message, history_dicts, endpoint_override, model=request.model):
   ```
   Replace with:
   ```
    async def event_generator():
        history_dicts = [{"role": e.role, "content": e.content} for e in request.history]
        prompt_message = request.message
        if request.web:
            try:
                sources = websearch.search_web(request.message)
                numbered = [{"n": i + 1, "title": s["title"], "url": s["url"]} for i, s in enumerate(sources)]
                payload = json.dumps({"sources": numbered})
                yield f'event: sources\ndata: {payload}\n\n'.encode()
                prompt_message = websearch.build_prompt(request.message, sources)
            except websearch.WebSearchError:
                yield b'event: sources\ndata: {"sources": [], "notice": "web search unavailable"}\n\n'
        try:
            for item in llm_mod.stream_reply(prompt_message, history_dicts, endpoint_override, model=request.model):
   ```
   (The sources event must be emitted BEFORE stream_reply is entered —
   AC-87 orders it ahead of every token.)

4. src/api/threads.py — EDIT (three anchored edits, one task; no
   dependency on 1-3).

   Edit A — the models currently begin exactly:
   ```
   class HistoryEntry(BaseModel):
   ```
   Replace with:
   ```
   class SourceLink(BaseModel):
       title: str
       url: str


   class HistoryEntry(BaseModel):
   ```

   Edit B — HistoryEntry's fields currently end exactly:
   ```
       model: str = ""
   ```
   Replace with:
   ```
       model: str = ""
       sources: list[SourceLink] | None = None
   ```

   Edit C — the PUT handler currently reads exactly:
   ```
       save_snapshot([t.model_dump() for t in payload.threads])
   ```
   Replace with:
   ```
       save_snapshot([t.model_dump(exclude_none=True) for t in payload.threads])
   ```
   (sources is None — not [] — when absent, and exclude_none drops it,
   so v45-shaped messages persist byte-identically: AC-91's second
   clause. No other field in these models can ever be None.)

5. src/static/index.html — EDIT (one edit). The composer currently
   contains exactly:
   ```
        <button type="button" class="think-toggle" id="think-toggle" data-testid="think-toggle" title="Toggle thinking display">💭</button>
   ```
   Insert directly BELOW that line:
   ```
        <button type="button" class="think-toggle" id="web-toggle" data-testid="web-toggle" title="Search the web for this message">🌐</button>
   ```
   Nothing else in the file changes.

6. src/static/threads.js — EDIT (three anchored edits, one task;
   depends on 5).

   Edit A — add the source-links renderer. The file currently contains
   exactly:
   ```
  function renderThreadMessages(thread) {
   ```
   Replace with:
   ```
  function addSources(bubble, sources, notice) {
    var box = document.createElement('div');
    box.className = 'msg-sources';
    box.setAttribute('data-testid', 'msg-sources');
    if (notice) {
      var n = document.createElement('span');
      n.className = 'web-notice';
      n.setAttribute('data-testid', 'web-notice');
      n.textContent = notice;
      box.appendChild(n);
    }
    for (var i = 0; i < sources.length; i++) {
      var a = document.createElement('a');
      a.className = 'source-link';
      a.setAttribute('data-testid', 'source-link');
      a.href = sources[i].url;
      a.target = '_blank';
      a.rel = 'noopener';
      a.textContent = '[' + (i + 1) + '] ' + (sources[i].title || sources[i].url);
      box.appendChild(a);
    }
    bubble.appendChild(box);
  }

  function renderThreadMessages(thread) {
   ```

   Edit B — re-render persisted sources (AC-91). renderThreadMessages
   currently contains exactly:
   ```
      addBubbleChrome(bubble, msg.content, msg.ts || 0, msg.role === 'assistant' ? (msg.model || '') : '', i);
   ```
   Replace with:
   ```
      addBubbleChrome(bubble, msg.content, msg.ts || 0, msg.role === 'assistant' ? (msg.model || '') : '', i);
      if (msg.role === 'assistant' && msg.sources && msg.sources.length) addSources(bubble, msg.sources, '');
   ```

   Edit C — export. The return object currently begins exactly:
   ```
  return {
    persistThreads: persistThreads,
   ```
   Replace with:
   ```
  return {
    addSources: addSources,
    persistThreads: persistThreads,
   ```

7. src/static/app.js — EDIT (five anchored edits; keep the brief terse,
   edits only, 2500-char cap) — the DAG's FINAL task: depends_on MUST
   list EVERY other task id (1-6 and all three no_edit tasks; D-64).

   Edit A — anchor (exact): `      var thinkToggle = document.getElementById('think-toggle');`
   Append directly below:
   ```
      var webToggle = document.getElementById('web-toggle');
      var webArmed = false;
      webToggle.addEventListener('click', function () {
        webArmed = !webArmed;
        webToggle.classList.toggle('active', webArmed);
      });
   ```

   Edit B — anchor (exact): `            statusRam.textContent = ram;`
   Append directly below:
   ```
            webToggle.disabled = !d.web_configured;
            if (webToggle.disabled) { webArmed = false; webToggle.classList.remove('active'); }
   ```

   Edit C — anchor (exact, three lines):
   ```
        if (modelSelect.value) {
          bodyObj.model = modelSelect.value;
        }
   ```
   Append directly below:
   ```
        if (webArmed) bodyObj.web = true;
        webArmed = false;
        webToggle.classList.remove('active');
        var pendingSources = [];
        var pendingNotice = '';
   ```

   Edit D — anchor (exact): `            if (eventType === 'token') {`
   Replace with:
   ```
            if (eventType === 'sources') {
              try {
                var sd = JSON.parse(dataStr);
                pendingSources = sd.sources || [];
                pendingNotice = sd.notice || '';
              } catch (err) {}
            } else if (eventType === 'token') {
   ```

   Edit E — anchor (exact): `              currentThread.messages.push({ role: 'assistant', content: replyText, ts: now, model: modelSelect.value || '' });`
   Replace with:
   ```
              var am = { role: 'assistant', content: replyText, ts: now, model: modelSelect.value || '' };
              if (pendingSources.length) am.sources = pendingSources.map(function (s) { return { title: s.title, url: s.url }; });
              currentThread.messages.push(am);
              if (pendingSources.length || pendingNotice) setTimeout(function () { Threads.addSources(replyBubble, pendingSources, pendingNotice); }, 0);
   ```
   (setTimeout defers addSources past the done-branch's later renderReply,
   which replaces innerHTML and would erase an eager append.)

no_edit_files (D-65 — never sent to the coder, acceptance still runs):
src/static/markdown.js, src/static/rain.js, src/static/style.css

Contract ids per task: contracts = [] — an EMPTY list for ALL tasks.
NEVER invent module-style ids.

Oracle Mapping — sixteen NEW node-ids this milestone:
- tests/test_websearch_service.py::test_unconfigured_when_key_missing
  -> maps to the src/services/websearch.py task.
- tests/test_websearch_service.py::test_configured_with_key
  -> maps to the src/services/websearch.py task.
- tests/test_websearch_service.py::test_search_sends_bearer_and_query
  -> maps to the src/services/websearch.py task.
- tests/test_websearch_service.py::test_search_returns_at_most_four_sources
  -> maps to the src/services/websearch.py task.
- tests/test_websearch_service.py::test_source_content_capped
  -> maps to the src/services/websearch.py task.
- tests/test_websearch_service.py::test_search_http_error_raises
  -> maps to the src/services/websearch.py task.
- tests/test_websearch_service.py::test_build_prompt_numbers_sources_and_keeps_question
  -> maps to the src/services/websearch.py task.
- tests/test_websearch_api.py::test_status_reports_web_configured
  -> maps to the src/api/status.py task.
- tests/test_websearch_api.py::test_web_false_issues_no_search
  -> maps to the src/api/chat.py task.
- tests/test_websearch_api.py::test_web_true_emits_sources_before_tokens
  -> maps to the src/api/chat.py task.
- tests/test_websearch_api.py::test_web_true_augments_prompt
  -> maps to the src/api/chat.py task.
- tests/test_websearch_api.py::test_search_failure_falls_back_with_notice
  -> maps to the src/api/chat.py task.
- tests/test_websearch_api.py::test_put_threads_roundtrips_sources
  -> maps to the src/api/threads.py task.
- tests/test_ui_websearch.py::test_web_toggle_present_default_off
  -> maps to the src/static/app.js task (the DAG's final task).
- tests/test_ui_websearch.py::test_web_reply_shows_source_links_and_toggle_resets
  -> maps to the src/static/app.js task.
- tests/test_ui_websearch.py::test_sources_persist_across_reload
  -> maps to the src/static/app.js task.
Transcribe the dependency edges literally; do not infer or omit any.
ALL other node-ids are carried forward — do NOT map them (the shell
auto-assigns regression, D-57).

Test dependencies: the browser tests observe web-toggle, msg-sources,
source-link (new testids, locked in contracts.ui) plus existing locked
testids/routes. conftest.py is amended in this same freeze (the LLM stub
gains a capture-shaped Tavily /search route; the app under test gets
TAVILY_API_KEY + TAVILY_ENDPOINT pointed at the stub — sandbox-safe under
--network none). One new external with frozen capture
(captures/tavily-search.json). No new stack imports.
