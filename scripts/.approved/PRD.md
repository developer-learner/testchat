PRD — testchat M26: Web Search Ratify (erd_version 49)

Milestone

M25 web search shipped, was CEO-demoed live (2026-07-17: real Tavily,
real MLX-served reply, real clickable sources under the bubble), and
five live-fixes landed same-day in the CEO session to close the gap
between the frozen spec and what the demo actually needed:

1. `src/main.py` — `python-dotenv` boot-load so `TAVILY_API_KEY` from
   `.env` reaches the running app (the AC-90 status flag would otherwise
   report false against a real key, greying the toggle).
2. `src/static/style.css` — visible armed/disabled treatment for the
   web toggle (dim+grayscale off, full-color+ring on) plus the
   source-link list styling. The frozen spec locked behavior and
   testids; visuals were deferred out of the freeze and only implemented
   under CEO eyes.
3. `src/static/app.js` — client-side normalization of Qwen-style
   citations `【N†anchor】` to plain `[N]`, before render, so the
   numbered form matches the source list a user sees.
4. `src/services/websearch.py` — sharpened prompt: instructs the model
   to cite as `[N]` in plain brackets and to prefer the most
   specific/recent number when sources disagree.

M26 ratifies all four: the ERD says "NO EDIT NEEDED" for every file,
two new ACs describe the ratified behavior, and three frozen tests pin
what the coder must not later break.

Acceptance Criteria (new — ratifying live behavior)

- AC-92: WHEN the assistant reply text contains a citation marker of
  the form `【N…】` (Chinese full-width brackets, an integer N, optional
  dagger and label text), the rendered reply SHALL display it as `[N]`.
- AC-93: WHEN the backend builds a web-augmented prompt, that prompt
  SHALL instruct the model to cite in plain `[N]` square-bracket form
  and to prefer the most specific/recent number when sources disagree.

Amended AC

- AC-90 (backend key wiring): the backend SHALL surface
  `web_configured: true` while `TAVILY_API_KEY` is set in the process
  environment — which, at runtime, includes a `.env` file loaded at
  application boot. (No behavior change; documents the load path M25's
  spec silently assumed.)

Out of scope for M26: broader answer-quality tuning (larger content
budget, tool-calling, iterative queries); "stop the toggle from
*looking* like the think toggle" (already visibly distinct via the
CSS pass).

Externals: unchanged from v47 (Tavily capture already frozen).

CEO Demo Script (already accepted 2026-07-17)

1. Restart app, reload page. Globe is dim/grayscale (default OFF).
2. Click globe → full-color with a ring (ON).
3. Send "what's the latest stable Python release?". Answer arrives
   with `[N]`-form citations and clickable source links under the
   bubble; sources open in a new tab.
4. Reload — the sourced reply keeps its links.
5. Accepted live 2026-07-17: real Tavily, four real sources,
   MLX-served reply, citations rendered as `[1]…[4]`.
