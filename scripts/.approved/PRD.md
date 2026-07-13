PRD — testchat M12: Ratify the Sprint

Milestone

M12 ratifies all features that landed in CEO-directed live sessions between
M9 (v19) and this freeze. No new code is written — the implementation
already exists. This milestone updates the frozen spec to match reality so
the oracle is honest and the suite is green.

Features ratified (all CEO-accepted in live sessions):

1. Block-level markdown renderer: fenced code blocks with copy button,
   headings (h1-h4), nested ordered/unordered lists with source numbering,
   blockquotes, horizontal rules, inline bold/italic/code/links.
2. Ten themes: light, dark, matrix, phosphor, midnight, neon, crisp, ember,
   graphite-amber, graphite-forest. Theme toggle cycles all ten.
3. Thread rename (inline edit + Enter to confirm, persisted via PUT /threads)
   and thread delete (with confirm dialog, persisted).
4. Auto-retitle: generic thread titles ("New Chat", "hi") replaced by first
   assistant reply content.
5. Send/Stop toggle: AbortController cancels the stream; partial reply and
   user message are retained.
6. Status strip: model indicator, RAM usage, nemotron RSS, live + average
   tokens/second.
7. System prompt: settings modal (gear button), textarea, Save/Cancel.
   Environment variable LLM_SYSTEM_PROMPT is authoritative when present.
8. Focus/fullscreen mode: toggle hides sidebar/top-bar/status-strip;
   browser Fullscreen API on .app-wrapper div with webkit prefix support.
9. Per-bubble hover chrome: copy and delete action buttons, timestamp and
   model metadata via data-attributes.
10. Blinking stream cursor during active streaming.
11. Centered 52rem reading column with symmetric gutters.
12. 30ms render throttle with streamEnded guard.

Acceptance Criteria

All v25 criteria remain in force. Amendments:

AC-53 (amended): WHEN the user clicks the theme toggle ten times, THE SYSTEM
SHALL cycle through all ten themes and return to the starting theme.

AC-55 (amended): WHEN the user cycles the theme toggle, THE SYSTEM SHALL
reach every theme including "neon", "crisp", "ember", "graphite-amber", and
"graphite-forest", and a full ten-click cycle SHALL return to the start.

manual-only waivers (D-58): all theme aesthetics (colors, contrast, glow
effects), markdown rendering appearance, bubble chrome layout, stream cursor
animation, column centering, and focus mode visual behavior are design —
verified by the CEO in live sessions, not automatable in headless browsers.

Out of Scope: app.js split (M13), new features.

CEO Demo Script: Already accepted — the CEO used every feature in live
sessions on 2026-07-11 and 2026-07-12. This milestone is paperwork.
