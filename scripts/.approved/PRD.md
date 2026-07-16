PRD — testchat M24: History Never Dies (maintenance milestone)

Milestone

testchat is feature-complete; M24 closes the one critical data-safety hole
a PM audit found (2026-07-15). The entire chat history is a single file
with a silent destruction path: if that file is ever unreadable, the app
starts fresh without saying so, and the very next save overwrites the
unreadable-but-recoverable original with the near-empty new state. M23
made SAVE failures visible; M24 does the same for the LOAD path, and adds
a one-save-deep backup so no save can destroy the only copy of anything.
A rider ratifies the 2026-07-15 hover-timestamp live-fix (past-day
messages showed a bare time, indistinguishable from today's).

Acceptance Criteria

- AC-78: WHEN the server loads the thread snapshot and the file exists
  but is not valid JSON, the server SHALL move that file aside to
  `<file>.corrupt-<timestamp>` in the same directory — bytes preserved —
  and serve an empty thread list.
- AC-79: WHILE at least one quarantined snapshot file exists beside the
  data file, GET /api/v1/threads SHALL report `"quarantined": true`;
  otherwise `"quarantined": false`.
- AC-80: WHEN the page loads and the threads response reports quarantined
  true, the status strip SHALL display "history unreadable (backup kept)"
  in the history-status element.
- AC-81: WHILE no quarantine exists, the history-status element SHALL be
  empty.
- AC-82: WHEN a snapshot save replaces an existing snapshot file, the
  replaced file's content SHALL survive as `<file>.bak` beside the data
  file (each save rotates: .bak always holds exactly the previous
  snapshot).
- AC-83 (ratifies the 2026-07-15 live-fix): WHEN a message's stored
  timestamp falls on a calendar day other than today, its hover meta
  SHALL include the calendar date ahead of the time. (Same-day messages
  keep time-only display — existing behavior, not separately pinned.)
- All prior ACs unchanged in intent. Four frozen tests are AMENDED in
  this freeze because they pinned exact shapes this milestone legitimately
  extends (each amendment listed in the delta):
  - test_threads_api.py::test_get_with_no_saved_data_returns_empty,
    ::test_delete_clears_snapshot, and ::test_put_invalid_role_rejected
    (its preserved-state assert) — the GET response gains the AC-79
    `quarantined` field.
  - test_storage_service.py::test_save_overwrites_atomically — the
    no-residue allowlist admits the deliberate AC-82 `.bak` artifact.

D-68 failure-visibility accounting: the quarantine rename itself failing
(exotic: permissions flipped between read and rename) is logged but not
user-visible — accepted residual risk, because the same conditions make
the next save fail, which AC-75/76 already surface as "not saved". A .bak
rotation failure fails the whole save and is likewise caught by AC-75/76.

Maintenance riders (no new app-behavior ACs; land with this freeze):

- conftest hardening: the persistence-isolation fixture compared the GET
  body to an exact dict — the AC-79 field would have silently broken every
  UI test's settle loop; it now checks the threads list only, and sweeps
  quarantine files between tests (the AC-79 flag is file-existence based
  and deliberately sticky).
- storage.py's tmp-cleanup `except OSError: pass` gains its justification
  comment (audit note from 2026-07-14, riding this milestone's touch of
  the file as planned).

Out of Scope: automatic restore from .bak or quarantine files (recovery
is a deliberate human act on a single-user app); generational/daily
backups (design sketched, deferred until wanted); multi-tab conflict
detection (unchanged from M23); pruning think-text from stored history
(size horizon is ~6 months away).

CEO Demo Script

1. Open the app with a healthy history — status strip shows nothing new.
2. Stop the backend; hand-corrupt data/threads.json (any stray character);
   restart; reload the page — "history unreadable (backup kept)" appears,
   the app starts empty, and a threads.json.corrupt-<ts> file sits in
   data/ with the full original content.
3. Send a message, then check data/: the new snapshot saved, the
   quarantine file untouched. Restore it by renaming it back over
   threads.json (optional live proof: reload — history returns).
4. Hover any bubble from a previous day — the tooltip reads e.g.
   "Jul 12 21:31", not a bare "21:31".
