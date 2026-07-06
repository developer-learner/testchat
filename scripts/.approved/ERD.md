ERD — testchat M5: Model Selection & Nemotron Runtime (erd_version 5)

What changes M4 → M5

New: src/services/models.py — LM Studio model-list proxy, Nemotron subprocess lifecycle (spawn, readiness poll, terminate), and a loaded-state check.
New: src/api/models.py — route handlers for GET /api/v1/models, POST /api/v1/nemotron/load, POST /api/v1/nemotron/unload.
Modified: src/api/chat.py — ChatRequest gains an optional model field (string, default null). Route handler resolves routing target (Nemotron vs LM Studio) before calling stream_reply, and returns 422 if model is present but not a string, or is "nemotron" while Nemotron is not loaded.
Modified: src/services/llm.py — stream_reply gains an endpoint_override parameter (default None). When set, the upstream POST target is endpoint_override instead of the LLM_ENDPOINT env var. All other behavior (message construction, history insertion, streaming, failure classification, StreamChunk protocol) is unchanged.
Modified: src/static/index.html — adds a model selector populated from GET /api/v1/models, and Load/Unload Nemotron controls. Selector locks after the first message of a conversation is sent; unlocks on refresh (which already resets history per M4).
Unchanged: src/main.py, GET /, SSE wire format, StreamChunk tagged union, FALLBACK_REPLY, history mechanics (AC-1 through AC-11 of M4), all M3 streaming/failure-handling paths.
Removed: nothing.

File inventory (M5 build)

src/services/models.py — new
src/api/models.py — new
src/services/llm.py — modified
src/api/chat.py — modified
src/static/index.html — modified

Data models

ChatRequest — extended: { "message": str, "history": list[HistoryEntry] = [], "model": str | None = None }. A model value other than "nemotron" is accepted and ignored for routing purposes (passed through as-is to the LM Studio path, consistent with LM Studio's own tolerance of client-supplied model strings).
ModelInfo — { "id": str, "source": "lmstudio" | "nemotron" }.
ModelsListResponse — { "models": list[ModelInfo] }.
NemotronLoadResponse — { "status": "loaded" | "error", "message": str | None }.
NemotronUnloadResponse — { "status": "unloaded" | "error", "message": str | None }.

Module contract for src/services/models.py (constraints — implementation detail specified here because the oracle tests patch against it directly, per TPM authoring discretion where no gate otherwise pins the seam):

Imports subprocess and httpx at module level (not aliased, not wrapped) so tests can monkeypatch models.subprocess.Popen and models.httpx.get directly.
Tracks the spawned Nemotron process in a module-level variable named _nemotron_process (None when not loaded).
Exposes module-level constants NEMOTRON_BASE_URL = "http://localhost:8000", NEMOTRON_CHAT_ENDPOINT = NEMOTRON_BASE_URL + "/v1/chat/completions", NEMOTRON_READY_URL = NEMOTRON_BASE_URL + "/v1/models", NEMOTRON_SCRIPT_PATH = "~/nemotron-vmlx.py" (expanded via os.path.expanduser at call time), NEMOTRON_READY_TIMEOUT_SECONDS = 30, NEMOTRON_TERMINATE_GRACE_SECONDS = 5.
list_models() -> list[dict]: reads LLM_ENDPOINT from os.environ (C-3, carried), derives the LM Studio base by stripping the /chat/completions suffix, calls httpx.get(base + "/v1/models"); on any exception or non-2xx, treats the LM Studio portion as empty. Appends {"id": "nemotron", "source": "nemotron"} if and only if is_nemotron_loaded() is true.
is_nemotron_loaded() -> bool: true if _nemotron_process is not None and its poll() reports still-running.
load_nemotron() -> dict: idempotent if already loaded; otherwise spawns via subprocess.Popen(["python3", expanded_script_path]), stores the handle in _nemotron_process, polls NEMOTRON_READY_URL via httpx.get in a loop up to NEMOTRON_READY_TIMEOUT_SECONDS; on success returns {"status": "loaded"}; on timeout, terminates the process, clears _nemotron_process, returns {"status": "error", "message": ...}.
unload_nemotron() -> dict: idempotent if not loaded; otherwise calls _nemotron_process.terminate(), waits up to NEMOTRON_TERMINATE_GRACE_SECONDS, escalates to kill() if still running, clears _nemotron_process, returns {"status": "unloaded"}.

stream_reply — stream_reply(message: str, history: Sequence[dict[str, str]] = (), endpoint_override: str | None = None) -> Iterator[StreamChunk]. When endpoint_override is not None, the upstream POST target is endpoint_override; otherwise LLM_ENDPOINT is read from os.environ as in M3/M4 (C-3 carried). Message/history construction, streaming, and failure classification are unchanged.
StreamChunk — unchanged from M3/M4.
SSE wire frames — unchanged from M3/M4.

Configuration (read at request time — C-3, carried)
Env var | Default | M5 change
LLM_ENDPOINT | http://localhost:1234/v1/chat/completions | none (LM Studio base for /v1/models is derived from this, not a new var)
LLM_MODEL | local-model | none
LLM_SYSTEM_PROMPT | `` (empty) | none
LLM_TIMEOUT_SECONDS | 120 | none
No new environment variables introduced (A3).

Key flows

Model list. Page loads → GET /api/v1/models → models.py calls list_models() → LM Studio queried at derived base URL; on failure, LM Studio portion is empty; Nemotron entry appended only if loaded → page populates selector.
Nemotron load. User clicks Load Nemotron → POST /api/v1/nemotron/load → models.py spawns the runtime, polls readiness → success returns "loaded", failure terminates and returns 503/"error" → page adds "nemotron" to the selector on success.
Nemotron unload. User clicks Unload Nemotron → POST /api/v1/nemotron/unload → models.py terminates the tracked process → page removes "nemotron" from the selector.
Chat routed to Nemotron. Page sends {"message":..., "history":[...], "model":"nemotron"} → chat.py checks is_nemotron_loaded(); if false, 422; if true, calls stream_reply(..., endpoint_override=NEMOTRON_CHAT_ENDPOINT) → identical SSE mechanics to M3/M4 from that point.
Chat routed to LM Studio (default/unchanged). model absent, null, or any non-"nemotron" string → chat.py calls stream_reply(...) with endpoint_override=None → identical to M4 behavior.
Selector lock. Page JS locks the selector control on first successful message send in a conversation; refresh (which already resets history per M4) also resets the lock and re-fetches the model list.

Constraints
M3 constraints C-1 through C-7 and M4's C-8/C-9 carry forward unchanged. Additions:

C-10 (routing boundary). chat.py is solely responsible for resolving model → endpoint_override and for the 422 checks in AC-11/AC-12. stream_reply performs no model-awareness of its own beyond accepting the override — this keeps C-6 layering intact.
C-11 (no shared mutable state beyond _nemotron_process). Nemotron lifecycle state lives only in src/services/models.py; no other module tracks or duplicates it.

Oracle Mapping (AC → test node)
Carried from M3/M4 (all remain in force, same test nodes — see M4 ERD for the full list; unchanged by M5).

M5-specific (new)

AC-1 → tests/test_models_api.py::test_list_models_includes_lmstudio_entries
AC-2 → tests/test_models_api.py::test_list_models_degrades_when_lmstudio_unreachable
AC-3 → tests/test_models_api.py::test_list_models_omits_nemotron_when_not_loaded
AC-4 → tests/test_models_api.py::test_load_nemotron_spawns_and_confirms_ready
AC-5 → tests/test_models_api.py::test_load_nemotron_idempotent_when_already_loaded
AC-6 → tests/test_models_api.py::test_load_nemotron_timeout_returns_503_and_terminates
AC-7 → tests/test_models_api.py::test_unload_nemotron_terminates_process
AC-8 → tests/test_models_api.py::test_unload_nemotron_idempotent_when_not_loaded
AC-9 → tests/test_chat_model_routing.py::test_chat_routes_to_nemotron_when_selected
AC-10 → tests/test_chat_model_routing.py::test_chat_routes_to_lmstudio_when_model_absent_or_other
AC-11 → tests/test_chat_model_routing.py::test_chat_invalid_model_type_is_422
AC-12 → tests/test_chat_model_routing.py::test_chat_nemotron_selected_but_not_loaded_is_422
AC-13 through AC-17 → CEO Demo Script (frontend, no automated harness — consistent with M1–M4 treatment of index.html)

Milestone Justification (D-46)
One milestone. Listing models and Nemotron load/unload are both prerequisites for the same visible feature — a working model selector — and neither is independently CEO-checkable without the other (a selector with nothing but LM Studio's already-known model, or a load/unload control with nothing to select into, both fail the D-44 bar). The backend surface is small (two new thin-proxy-style routes plus one routing branch in an existing route); the frontend addition is one control cluster. Fits one freeze cycle.

Test dependencies
pytest, fastapi.testclient.TestClient, unittest.mock (for subprocess and httpx patching) — httpx added as a new test-time dependency for this module; not an src.* observation and does not affect the surface gate (INV-4).
