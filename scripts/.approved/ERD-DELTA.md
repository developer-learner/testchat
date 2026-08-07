ERD Delta — testchat spec v83: contracts entry→file pins (the 40-entry backfill, D-120 prerequisite) — no product behavior changes

This is a spec-bookkeeping freeze. Every route, schema, and error entry in
contracts.json gains a "file" pin naming the source file whose code must
satisfy it, so the EM's per-milestone plan context can be sliced to the
files the milestone touches (D-120: the slice generator is live but inert
until pins exist — this freeze is what activates it). No product behavior
changes; no entry body is altered.

## Changed acceptance criteria

None. No acceptance criterion is added, modified, or retired by this
freeze. contracts.changed_files is [] by declaration — the delta's scope is
spec metadata only.

## Superseded acceptance criteria

None.

## Changed files

No source or test file changes. contracts.files is unchanged
(src/static/app.js, src/static/index.html); the frozen suite is untouched.

Pin ownership notes for the split-ownership entries (the EM prompt should
name the ambiguity, per the D-120 proposal):

- error:422-validation is pinned to src/api/chat.py. Request-validation 422s
  are produced by every validated endpoint — ChatRequest in
  src/api/chat.py, ThreadsPayload in src/api/threads.py, settings payloads
  in src/api/settings.py — and chat.py is the primary validated surface.
- schema:HistoryEntry is pinned to src/api/chat.py. It is defined in both
  src/api/chat.py (ChatRequest.history) and src/api/threads.py
  (ThreadSnapshot.messages) with identical shapes.

All other pins are single-owner: routes → the handler file (GET / and
/static/{path} → src/main.py; model/nemotron/script-model routes →
src/api/models.py; threads → src/api/threads.py; settings →
src/api/settings.py; status → src/api/status.py); schemas → the file that
defines the request/response model or emits the shape (SSE event shapes →
src/api/chat.py; SourceLink and the ThreadSnapshot family →
src/api/threads.py; StatusResponse → src/api/status.py); errors → the file
that raises them (409-revision-conflict → src/api/threads.py; both 503s →
src/api/models.py, the script-model load path).

## Test-to-file mapping

Unchanged. This freeze stages no test changes; the frozen suite and its
behavioral-ownership mapping are untouched.
