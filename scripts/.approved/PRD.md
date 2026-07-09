PRD — testchat M8: Persistence (Threads Survive Everything)

Milestone

M8 makes conversations durable. Today every thread lives only in the page's
memory; refresh, browser restart, or machine restart erases them. After M8,
the app keeps all threads in a data file it owns — any browser on this
machine, any time, sees the same history. No accounts, no logins, no
network storage: single-user, local, private.

This milestone SUPERSEDES AC-25 (M6: "refresh clears all threads"). The new
law is the opposite: refresh restores.

What

Backend:
- A storage service that saves and loads the full thread snapshot as one
  JSON file (path from env TESTCHAT_DATA, default data/threads.json),
  written atomically (temp file + rename), tolerant of a missing or corrupt
  file (both read as "no saved threads").
- Three routes: GET /api/v1/threads (the saved snapshot),
  PUT /api/v1/threads (replace the snapshot), DELETE /api/v1/threads
  (clear it — used by tests and as a future "clear history" hook).

Frontend (src/static/app.js, edit-mode changes only):
- On page load, fetch the saved snapshot and rebuild the threads array,
  sidebar, and active thread from it; fall back to today's single fresh
  "New Chat" thread when the snapshot is empty or the fetch fails.
- Persist the snapshot (PUT, fire-and-forget) at the moments state becomes
  worth keeping: when an assistant reply completes ('done') and when a new
  thread is created (which also captures the auto-title of the previous
  thread).

Acceptance Criteria (EARS notation)

All M3–M7 criteria remain in force except AC-25, which this milestone
replaces. AC-34 is a frozen Playwright UI test (D-58); AC-35..AC-38 are
frozen backend tests.

AC-34 [replaces AC-25]: WHEN the page is loaded and a saved snapshot
exists, THE SYSTEM SHALL display the saved threads — sidebar titles,
messages, and each thread's model-lock state — with the previously active
behavior available (send continues the thread).

AC-35: WHEN an assistant reply completes, THE SYSTEM SHALL persist the
snapshot such that a subsequent GET /api/v1/threads returns the updated
thread.

AC-36: WHEN GET /api/v1/threads is called with no saved data, THE SYSTEM
SHALL return an empty threads array (HTTP 200, never an error).

AC-37: WHEN PUT /api/v1/threads receives a valid payload, THE SYSTEM SHALL
store it so that a following GET returns an equal payload; WHEN the payload
is malformed, THE SYSTEM SHALL return 422 and leave the stored snapshot
unchanged.

AC-38: WHEN the snapshot file is missing or contains invalid JSON, THE
SYSTEM SHALL treat it as empty (load returns []) rather than failing.

manual-only waivers (D-58):
- Restart-the-Mac durability: same file-on-disk property AC-38 tests;
  physically restarting hardware stays a CEO check.
- Cross-browser visibility (Chrome vs Safari): same-snapshot-by-
  construction; spot-check at the demo.

Out of Scope

Accounts, logins, or multi-user anything.
Cloud/remote storage or sync between machines.
Draft preservation (text typed but not sent is not saved).
Thread deletion/renaming UI (DELETE route exists; no button yet).
Saving mid-stream partial replies (a reply persists when it completes).
The M9 polish items: Nemotron-unload crash dialog, port-8000 collision,
error-path history retention.

Flagged Assumptions (CEO sign-off at the freeze gate)

A14: Storage is one JSON file owned by the app — not a database engine.
Same durability at this scale, far fewer moving parts; a future multi-user
milestone would replace only the storage service.
A15: Concurrent tabs are last-write-wins. Two tabs chatting simultaneously
will overwrite each other's snapshot; single-user local app, accepted.
A16: Persistence moments are reply-completion and thread-creation. A crash
between those moments loses at most the in-flight exchange.

CEO Demo Script

Chat in two threads. Hit refresh — both threads return, titles intact,
lock states intact. Quit the browser entirely; reopen — still there.
Open the app in a different browser — same threads. Restart the Mac if
you're feeling thorough — still there.
