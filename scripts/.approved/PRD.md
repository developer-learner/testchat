PRD — testchat M27: DeepSeek V4 Flash (erd_version 50)
Milestone
Add DeepSeek V4 Flash as a second script-run local model, peer to nemotron. Same lifecycle (load / unload from the UI, mutual exclusion because both are RAM-heavy), same shape at the wire, different backing server binary.
Motivation
testchat is in maintenance mode per the 2026-07-17 CEO directive, but the CEO overrode the freeze to add a new model source: the DeepSeek V4 Flash MoE (`ddalcu`-style local serve is not applicable; ds4 runs its own OpenAI-compatible server at 127.0.0.1:8000 via `/Users/arc.elixir/dev/ds4/run-server.sh`). Nemotron's single-model plumbing is generalized into a small script-model registry so the second model (and any future third) reuses the load / unload / status machinery instead of copy-pasting nemotron's endpoints.
Acceptance Criteria

* AC-94: WHEN the user clicks Load DeepSeek THEN the backend SHALL spawn the DeepSeek server via `/Users/arc.elixir/dev/ds4/run-server.sh`, poll its /v1/models endpoint at http://127.0.0.1:8000, and return `{"status":"loaded"}` within 180 s; otherwise it SHALL SIGINT the process, clear the handle, and return HTTP 503 with `{"status":"error","message":...}`.
* AC-95: WHEN the user clicks Unload DeepSeek THEN the backend SHALL SIGINT the process (5 s grace, SIGKILL after) and return `{"status":"unloaded"}`. Unload while the model was not loaded is a 200 no-op.
* AC-96: WHEN one script model is loaded and the user requests the other, THEN the backend SHALL unload the first before spawning the second (mutual exclusion — script models are RAM-heavy, only one runs at a time). Nemotron and DeepSeek follow the same rule.
* AC-97: WHEN a chat request selects `model="deepseek-v4-flash"` AND the DeepSeek server is loaded, THEN the backend SHALL stream the reply from http://127.0.0.1:8000/v1/chat/completions with `model="deepseek-v4-flash"` in the upstream body. If the server is NOT loaded, the request SHALL be rejected with HTTP 422 (same shape as nemotron-not-loaded).
* AC-98: WHEN the frontend queries GET /api/v1/models AND the DeepSeek server responds ready, THEN the response SHALL include `{"id":"deepseek-v4-flash","source":"deepseek-v4-flash"}` alongside any lmstudio or nemotron entries.
* AC-99: The load / unload endpoints SHALL be exposed generically at `POST /api/v1/script-models/{model_id}/load` and `.../unload`. The existing `POST /api/v1/nemotron/load` and `.../unload` remain as aliases (backwards compatibility for the frontend and any external scripts wired to them).
Amended AC
* AC-98 supersedes the source-enum wording from prior specs: the ModelInfo.source enum expands from `'lmstudio' | 'nemotron'` to `'lmstudio' | 'nemotron' | 'deepseek-v4-flash'`.
Out of scope for M27
* Any quality tuning or benchmarking of DeepSeek vs the MLX 4-bit default (deferred; the current default per D-72 is unchanged).
* A third-model UI presentation refresh (buttons kept the same shape as the nemotron pair; no new visual language).
* A generalized model-picker UI that lists loadable script models dynamically — the two buttons are hand-wired for now; if a fourth model lands, revisit.
* Any change to the mtplx / EM / coder role mapping.
Externals
* No new external declared. DeepSeek runs as a local subprocess (same category as nemotron, which also has no externals entry). If a future milestone probes the DeepSeek server's live shape we would add `external:deepseek-v4-flash-chat` with the capture then.
CEO Demo Script

1. Restart app, reload page.
2. Click Load DeepSeek. Wait for the button to re-enable; status strip should show DeepSeek loaded.
3. Select `deepseek-v4-flash` from the model dropdown.
4. Send a short prompt. Reply streams back from the DeepSeek server.
5. Click Load Nemotron. DeepSeek is unloaded first (mutual exclusion), then nemotron loads.
6. Click Unload Nemotron. Model dropdown returns to lmstudio-only.
M28d — test-only recut (deterministic AC-42 + themed AC-47)
Two frozen-test recuts; no new app features, no new routes.

AC-42 (recut — test infrastructure only):
The thinking-placeholder test is re-anchored from a wall-clock hold window to a gated stub protocol. App behavior is unchanged: WHEN think tokens arrive before answer tokens, the reply bubble SHALL show "thinking..." until the first visible-answer token clears it. The recut eliminates the timing race that caused flakes under memory load — the conftest SLOWPING handler now gates answer tokens behind a test-controlled release endpoint; the placeholder persists indefinitely until the test releases the gate.

AC-47 (recut — native dialog replaced by themed modal):
WHEN the user clicks thread-delete-btn, the delete-confirm-modal SHALL appear. The thread SHALL be removed only WHEN delete-confirm is clicked. IF delete-cancel is clicked, the modal SHALL close and the thread SHALL remain. The delete-confirm-modal is the same modal already used for message-pair delete; it gains three locked testids: delete-confirm-modal, delete-confirm, delete-cancel.
v57 — model dropdown: drop the "✓" selection prefix
* AC-100: The model-select option labels SHALL never contain "✓". The current thread's model SHALL be indicated solely by the native select's selected option — the OS renders its own checkmark, and the label glyph duplicated it ("✓ ✓" on macOS; CEO-rejected 2026-07-19). Load-state glyphs (○ / blinking / 🟢) and both confirm gates are unchanged.
