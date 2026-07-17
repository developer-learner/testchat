PRD — testchat M25: Web-Informed Answers (erd_version 46)

Milestone

The local models' knowledge is frozen at their training cutoff. M25 gives
a chat message the option to draw on live web content: a per-message
globe toggle in the composer. When ON, the backend queries Tavily
(purpose-built search API returning extracted page content — chosen over
snippet-scraping precisely because the weak local models need clean,
complete context, not fragments), injects the top results into the LLM
prompt as numbered sources, and the reply's sources render as clickable
links under the bubble. When OFF, behavior is byte-identical to v45.

Design rules fixed by the weak-model constraint (CEO-directed):
the model NEVER formulates the search (the user's message is the query —
no tool-calling, no query-rewriting hop); injection is bounded and rigidly
structured (at most 4 sources, per-source content capped, numbered, with
an explicit "cite by number" instruction).

Acceptance Criteria

- AC-84: WHEN the composer is rendered, it SHALL contain a web-search
  toggle (globe), default OFF; WHEN a message is sent, the toggle SHALL
  reset to OFF.
- AC-85: WHEN a message is sent with the toggle OFF, the backend SHALL
  issue no search request and process the message exactly as v45.
- AC-86: WHEN a message is sent with the toggle ON, the backend SHALL
  issue exactly one Tavily search using the user's message text as the
  query, before the LLM call.
- AC-87: WHEN the search succeeds, the backend SHALL inject at most 4
  sources (title, URL, extracted content capped at 2000 characters per
  source) into the LLM prompt as a numbered block ahead of the user's
  question, and SHALL emit an SSE `sources` event carrying the numbered
  title/URL list before any token events.
- AC-88: WHEN a web-informed reply is rendered, the UI SHALL display the
  sources as clickable links (opening in a new tab) beneath the reply
  bubble, numbered to match the injection.
- AC-89: IF the search fails for any reason (HTTP error, timeout at 10s,
  bad response), THEN the backend SHALL proceed with the normal
  un-augmented LLM call AND the reply SHALL carry a "web search
  unavailable" notice — a failed search never kills the chat.
- AC-90: WHILE `TAVILY_API_KEY` is unset on the backend, GET
  /api/v1/status SHALL report `"web_configured": false` and the toggle
  SHALL be disabled with a title naming the missing configuration.
  (manual-only: the disabled-toggle visual state — the app under UI test
  always runs configured; the status field and the backend refusal are
  frozen-tested.)
- AC-91: WHEN a web-informed exchange is persisted, the source list
  (title + URL per source) SHALL persist with the assistant message and
  re-render on thread reload. Messages without sources SHALL persist in
  the exact v45 shape (no new field).

Out of Scope: full-page fetching beyond Tavily's extracted content;
multi-query or iterative search; model-formulated queries (tool-calling);
auto-detecting when a message needs the web (the toggle is the only
trigger); persisting the failure notice (transient, live-render only);
visual styling polish for the source links (theme CSS untouched this
milestone — live-fix territory if wanted).

Externals (D-56): `external:tavily-search` — real response captured
2026-07-17 (captures/tavily-search.json) from a live probe. The mock and
all tests derive from that shape: top-level `results` array of
`{url, title, content, score, raw_content}`. The API key travels only as
an env var (`TAVILY_API_KEY`); `TAVILY_ENDPOINT` is overridable so the
sandboxed suite (--network none) binds a loopback stub.

Flagged assumptions (ruled 2026-07-17, CEO session): toggle resets after
every send; the raw user message is the query; sources persist in
history.

CEO Demo Script

1. Toggle the globe, ask something after the models' cutoff ("what
   happened with X this week") — the reply uses current information and
   shows numbered source links; click one, it opens the real page.
2. Same question, toggle off — the old offline behavior, no sources.
3. Reload the page — the web-informed reply still shows its sources.
4. Break the network (or unset the key and restart), toggle on, send —
   the reply still arrives, marked "web search unavailable".
