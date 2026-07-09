PRD — testchat M7: Browser Oracle Retrofit + Chat Hygiene Fixes (v11)

Milestone

M7 has two purposes, deliberately coupled:

1. Retrofit: the acceptance criteria of M5/M6 that broke silently (think
   rendering, per-thread model lock, thread switching) become frozen
   Playwright UI tests (D-58). The pipeline's oracle learns to see exactly
   what the CEO saw at the M6 demo.
2. Fixes: two defects found in review of the M6/hotfix code, both invisible
   to the old oracle, become spec'd behavior with covering UI tests:
   (a) stored conversation history is contaminated with <think> markup that
   gets re-sent to the model on every subsequent message; (b) the model list
   refresh after Nemotron load/unload silently resets the active thread's
   model selection.

v11 delta (after the v10 halt): same milestone, same acceptance criteria,
same frozen tests — the frontend is now split into three files
(index.html shell, app.js, style.css) plus a one-line static-files mount
in src/main.py, so each coder task is small and single-concern. The v10
single-task decomposition asked one 638-line full-file rewrite and the
coder deleted working features; the oracle caught it (efdda29). No SSE
wire format or API schema changes.

What

Frontend (src/static/index.html):

Locked DOM surface (D-58). Every element named in contracts.ui carries its
data-testid attribute. These are the only hooks the frozen UI tests use;
everything else in the DOM may be freely restructured.

Think handling — captured reality (external:lmstudio-chat-stream). Thinking
text arrives BOTH ways: as SSE 'think' events (reasoning_content configs)
and INLINE as <think>...</think> inside 'token' events (the current LM
Studio config — see the capture). The frontend renders thinking from either
source inside the reply bubble, wrapped in elements carrying
data-testid="think-content", hidden unless the global think toggle is on.

History hygiene (fix a). The per-thread messages array — and therefore the
history POSTed to /api/v1/chat — stores assistant content with ALL
<think>...</think> spans stripped. Thinking text is display-only, in the
live reply bubble. After a thread switch, re-rendered past messages show
final content only (thinking display does not persist across switches —
accepted, see A11).

Model-selection stability (fix b). Rebuilding the model dropdown (after
Nemotron load/unload) preserves the active thread's current selection when
that model is still in the list. A locked thread's selection is never
silently changed by a list refresh.

All M6 behavior (threads, sidebar, titles, per-thread lock) is otherwise
unchanged.

Acceptance Criteria (EARS notation)

All M3–M6 acceptance criteria remain in force. AC-27..AC-31 are frozen
Playwright UI tests (D-58); AC references in brackets name the earlier AC
they retrofit.

AC-27 [retrofits M5 think-streaming, broke in M6]: WHEN an assistant reply
contains thinking text (inline <think> tokens or 'think' events), THE SYSTEM
SHALL render it in the reply bubble inside think-content elements — hidden
WHILE the think toggle is off, visible WHILE it is on.

AC-28 [retrofits AC-23, broke in M6]: WHEN the user has sent a message in
thread A, THE SYSTEM SHALL disable the model selector in thread A, keep it
enabled in a newly created thread B, and restore the disabled state when the
user switches back to thread A.

AC-29 [retrofits AC-20/AC-22]: WHEN the user sends messages in two threads
and clicks between them in the sidebar, THE SYSTEM SHALL display exactly the
clicked thread's messages.

AC-30 [new — fix a]: WHEN the frontend POSTs to /api/v1/chat, THE SYSTEM
SHALL send a history whose assistant entries contain no <think> markup.

AC-31 [new — fix b]: WHEN the model list is refreshed via Nemotron
load/unload, THE SYSTEM SHALL preserve the active thread's model selection
if that model is still present in the new list.

AC-32 [retrofits AC-19]: WHEN the user clicks "New Chat", THE SYSTEM SHALL
add a thread to the sidebar and show an empty chat panel.

AC-33 [retrofits AC-21]: WHEN the user sends the first message in a thread,
THE SYSTEM SHALL set the thread's sidebar title from that message's leading
characters.

manual-only waivers (D-58 rule: every user-visible AC maps to a UI node-id
or carries a waiver):
- AC-24 (mid-stream thread switching): streaming-vs-click timing cannot be
  made deterministic without instrumenting the app; remains CEO-demo only.
- AC-25 (refresh clears state) and AC-26 (global Nemotron effect across
  threads): low-risk, exercised implicitly by every UI test's fresh page
  load; remain CEO-demo.

Out of Scope (documented defects, deferred to a later milestone)

- Error-path history retention: today a stream error loses the user's
  message from the thread history (only 'done' commits), and the thread's
  model lock can engage despite an empty committed history. Known defect,
  NOT fixed in M7.
- Concurrent streams: sending is globally disabled while any thread
  streams; the shared reply buffer must become per-send state before this
  can change. Known limitation, NOT fixed in M7.
- Mid-stream lock/scroll targeting the viewed thread instead of the sending
  thread. Known defect, NOT fixed in M7.
- Persistence, thread deletion/renaming, mobile responsiveness (unchanged
  from M6's out-of-scope list).

Flagged Assumptions (CEO sign-off at the freeze gate)

A11: Thinking text is ephemeral display — after switching away and back to
a thread, past replies show final content only. Re-showing historical
thinking would require storing it separately per message; not worth the
state complexity now.
A12: "Preserve selection" (AC-31) means by model id string match. If the
selected model disappears from the refreshed list, falling back to the
first option is acceptable.
A13: The UI test mock serves the captured LM Studio shapes with synthetic
content (D-56: shape from capture, content test-chosen).

CEO Demo Script

Open the page — one "New Chat" thread, model dropdown populated.
Send a message — reply streams; thinking hidden; toggle 💭 on — thinking
text appears greyed; toggle off — it hides.
Send a second message — reply still coherent (history clean; previously the
model was re-fed its own thinking).
New Chat — selector unlocked; send in thread 2 — selector locks; click
thread 1 — its messages and lock state return.
Select a model in a fresh thread, click Unload Nemotron — selection stays.
Start a long reply, switch threads mid-stream, switch back (AC-24 waiver —
manual): completed reply visible.
