ERD — testchat M9: Polish Sweep (erd_version 19)

What changes M8 → M9

Two existing files, edit-mode only (D-59 anchored blocks). No new files, no
new routes, no schema changes. Cut per D-60: each file gets tightly-related
edits about one subject.

File inventory (M9 build)

1. src/services/models.py — EDIT (subject: Nemotron address config)
   Replace the three hardcoded nemotron URL constants so they derive from an
   env var, read at import:
     NEMOTRON_BASE_URL   = os.environ.get("NEMOTRON_URL", "http://localhost:8600")
     NEMOTRON_CHAT_ENDPOINT = NEMOTRON_BASE_URL + "/v1/chat/completions"
     NEMOTRON_READY_URL     = NEMOTRON_BASE_URL + "/v1/models"
   KEEP the constant NAMES exactly (existing frozen tests monkeypatch them).
   `os` is already imported. Change nothing else — the shutdown path,
   signals, and timeouts are untouched this milestone.

2. src/static/app.js — EDIT (subject: reply-bubble robustness; two related
   edits in the streaming path)
   a. Failed-reply history retention (AC-41): in BOTH failure branches — the
      'error' event branch inside processFrame, and the fetch .catch at the
      end of the submit handler — push { role: 'user', content: message }
      into currentThread.messages (only if not already pushed) and call
      persistThreads(). Do NOT push an assistant message. Do not alter the
      'done' branch.
   b. "thinking..." placeholder (AC-42): right after the reply bubble is
      created, set its text to "thinking...". In the token/think render seam
      (where replyBubble.innerHTML = renderThink(replyText) runs), when the
      rendered VISIBLE text is empty (all content is think-spans or nothing),
      show "thinking..." instead; otherwise show the rendered result. The
      placeholder must never enter stored history (history is stripThink of
      replyText, which never contains it) and must not appear once visible
      answer text streams.

Data models

None changed.

Configuration

NEMOTRON_URL (env): Nemotron server base URL, default
http://localhost:8600. Read at models.py import.

Constraints

All prior constraints carry forward. New:
C-22: constant NAMES in models.py are part of the frozen test surface — the
config edit changes their VALUES' source, never their names.
C-23: the "thinking..." placeholder is display-only; it is never written to
thread.messages nor sent to the backend.

Contract ids per task (the validator rejects invented ids):
- src/services/models.py task: contracts = ["src.services.models"] (plus any
  of its locked symbols if you wish).
- src/static/app.js task: contracts = [] — an EMPTY list. Frontend files
  have no module entry points; ui:* ids are legal but optional. NEVER invent
  module-style ids (there is no 'src.static.app' in contracts.json).

Oracle Mapping (AC → test node) — guidance for the plan

- src/services/models.py task: map ALL node-ids whose test imports
  src.services.models — that is tests/test_nemotron_config.py::* (NEW, this
  freeze; imports ONLY src.services.models), PLUS the already-frozen
  tests/test_models_service.py::*, tests/test_models_api.py::*, and
  tests/test_chat_model_routing.py::* (each imports src.services.models and
  is attributed to this delta by the validator). All are collectable now
  (src.main already exists on disk) and must pass immediately after the
  models.py edit — the config change preserves constant names and the
  default is inert under the tests' mocks/monkeypatches.
- src/static/app.js task: map the two NEW UI node-ids
  tests/test_ui.py::test_failed_reply_keeps_user_message and
  ::test_thinking_placeholder_shows_then_clears, PLUS all existing
  tests/test_ui.py::* (they exercise the same file). This task depends_on
  the models.py task.
- Unmapped, shell-carried (D-57): test_llm_service.py, test_storage_service.py,
  test_chat_api.py, test_threads_api.py, test_page.py — none import
  src.services.models and none are UI tests, so they are not attributed to
  this delta.

Milestone Justification

Single milestone: two files, one subject each, every AC mechanically
checkable. The deferred crash-dialog item is explicitly separated because it
is not deterministically testable and needs live diagnosis.

Test dependencies

No new dependencies (existing pytest + playwright stack).
