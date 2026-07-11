PRD — testchat M9: Polish Sweep (three deterministic fixes)

Milestone

M9 fixes three defects the CEO hit during the M7/M8 demos. Each is small,
one concern, and mechanically testable. A fourth known defect — the macOS
"Python quit unexpectedly" dialog on Nemotron unload — is deliberately NOT
in this milestone (see "Deferred" below): its cause is not deterministically
reproducible in the test sandbox and the app's existing SIGINT shutdown was
already the intended fix, so it needs live diagnosis on the real model, not
a blind spec.

What

1. Configurable Nemotron address (src/services/models.py).
   The Nemotron server address is hardcoded to localhost:8000 — the port the
   app itself commonly uses, so "Load Nemotron" fails whenever the app holds
   8000 (the CEO hit this at the M7 demo). Make it configurable via env var
   NEMOTRON_URL, default http://localhost:8600 (a port nothing else here
   uses). Same pattern as the already-configurable LLM_ENDPOINT.

2. Failed replies keep the user's message (src/static/app.js).
   Today a message is saved into the thread only on a 'done' event. If the
   reply ends in 'error' or the network fails, the user's sent message
   vanishes from stored history, and the thread can be left locked with no
   messages. Fix: on failure, retain the user's message in history and
   persist it (store no assistant message for the failed reply).

3. "Thinking..." placeholder (src/static/app.js).
   Some local models reason silently for minutes before any visible answer;
   the reply bubble is blank the whole time and the app looks frozen (CEO-
   reported, M8 demo). While a reply is in flight and no visible answer text
   has rendered yet, the bubble shows "thinking...", which disappears the
   moment visible answer text arrives.

Acceptance Criteria (EARS notation)

All prior criteria remain in force. AC-39/40 are frozen backend tests;
AC-41/42 are frozen Playwright UI tests (D-58).

AC-39: WHEN NEMOTRON_URL is unset, THE SYSTEM SHALL address the Nemotron
server at http://localhost:8600 for its chat and readiness endpoints.

AC-40: WHEN NEMOTRON_URL is set, THE SYSTEM SHALL derive the Nemotron chat
and readiness endpoints from that value.

AC-41: WHEN a chat reply ends in an error event or the request fails, THE
SYSTEM SHALL keep the user's sent message in the thread's stored history
(retrievable after a thread switch) and persist it, and SHALL store no
assistant message for the failed reply.

AC-42: WHILE a reply is streaming and no visible answer text has rendered
yet, THE SYSTEM SHALL show "thinking..." in the reply bubble; WHEN visible
answer text renders, THE SYSTEM SHALL replace the placeholder with it.

Out of Scope / Deferred

- The Nemotron-unload macOS crash dialog. The app already sends SIGINT (the
  original intended fix); the dialog persists, so the cause is elsewhere
  (child exits on a traceback, or the signal misses the child's process
  group). Fixing it blind would be an untestable OS-behavior guess. It stays
  open for a live load/unload investigation on the real model with the CEO.
- Any change to the shutdown SIGNAL (the four frozen tests asserting SIGINT
  stay valid this milestone).
- Accounts, remote access, thread deletion UI, search — future milestones.

Flagged Assumptions (CEO sign-off at the freeze gate)

A17: 8600 is a safe default Nemotron port (nothing else in this stack uses
it). The operator can still override with NEMOTRON_URL.
A18: The placeholder is the literal text "thinking..." — no spinner/anim
(kept deterministic for the frozen UI test; animation is a future nicety).

CEO Demo Script

Run the app on 8080; NEMOTRON_URL unset. Load Nemotron — it now binds 8600
and loads without the port clash. Send a message to a model that fails
(e.g. stop LM Studio mid-reply) — your message stays in the thread. Send to
a slow local model — the bubble shows "thinking..." until the answer starts.
