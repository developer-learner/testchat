ERD — testchat M5: Model Selection & Nemotron Runtime (erd_version 8 — re-trued to shipped behavior)

What changes M5 v7 spec → M5 v8 shipped reality

The v7 spec assumed LM Studio's OpenAI-compatible /v1/models endpoint returns loaded-model information. In practice, /v1/models returns all discovered models regardless of load state; the actual loaded-instance data lives at LM Studio's native REST API /api/v1/models, response shape {"models": [{"key": ..., "loaded_instances": [...]}, ...]}. is_nemotron_loaded was specified as a process-poll check; in practice it is an HTTP readiness probe so the app tolerates Nemotron processes it did not spawn. Shutdown used SIGTERM which produced a macOS crash dialog; in practice SIGINT is used (Ctrl+C equivalent). The selected model name was not passed through to the upstream request, causing LM Studio to reject model "local-model". A new SSE event: think frame carries reasoning_content tokens. The frontend renderThink() function had a broken regex that was restored, and the load/unload handlers now refresh the model list on success.

File inventory (M5 build — unchanged from v7)

src/services/models.py — new
src/api/models.py — new
src/services/llm.py — modified
src/api/chat.py — modified
src/static/index.html — modified

Data models (unchanged from v7)

ChatRequest — extended: { "message": str, "history": list[HistoryEntry] = [], "model": str | None = None }.
ModelInfo — { "id": str, "source": "lmstudio" | "nemotron" }.
ModelsListResponse — { "models": list[ModelInfo] }.
NemotronLoadResponse — { "status": "loaded" | "error", "message": str | None }.
NemotronUnloadResponse — { "status": "unloaded" | "error", "message": str | None }.

Module contract for src/services/models.py (v8 revision)

Imports subprocess, signal, and httpx at module level (not aliased, not wrapped) so tests can monkeypatch models.subprocess.Popen, models.signal, and models.httpx.get directly.

Tracks the spawned Nemotron process in a module-level variable named _nemotron_process (None when not loaded or not tracked).

Exposes module-level constants: NEMOTRON_BASE_URL = "http://localhost:8000", NEMOTRON_CHAT_ENDPOINT = NEMOTRON_BASE_URL + "/v1/chat/completions", NEMOTRON_READY_URL = NEMOTRON_BASE_URL + "/v1/models", NEMOTRON_SCRIPT_PATH = "~/nemotron-vmlx.py" (expanded via os.path.expanduser at call time), NEMOTRON_READY_TIMEOUT_SECONDS = 30, NEMOTRON_TERMINATE_GRACE_SECONDS = 5.

list_models() -> list[dict]: reads LLM_ENDPOINT from os.environ (C-3, carried), derives the LM Studio base by stripping the /v1/chat/completions suffix, calls httpx.get(base + "/api/v1/models"); on any exception or non-2xx, treats the LM Studio portion as empty. Iterates models from the JSON response key "models", includes only those with a truthy loaded_instances list, using the model's "key" field as the model id. Appends {"id": "nemotron", "source": "nemotron"} if and only if is_nemotron_loaded() is true.

is_nemotron_loaded() -> bool: probes NEMOTRON_READY_URL via httpx.get with a 2-second timeout. Returns True on HTTP 200, False on any exception or non-2xx. Does NOT check _nemotron_process — the probe is independent of process tracking so the app detects externally started Nemotron instances as loaded.

load_nemotron() -> dict: idempotent if is_nemotron_loaded() is already true; otherwise spawns via subprocess.Popen(["python3", expanded_script_path]) (expanduser applied before the call, not left to the OS), stores the handle in _nemotron_process, polls NEMOTRON_READY_URL via httpx.get in a loop up to NEMOTRON_READY_TIMEOUT_SECONDS, also checks process.poll() each iteration to detect early subprocess death. On success returns {"status": "loaded"}; on timeout or process death, sends signal.SIGINT to the subprocess, waits up to NEMOTRON_TERMINATE_GRACE_SECONDS, escalates to kill() if still running, sets _nemotron_process to None, returns {"status": "error", "message": ...}.

unload_nemotron() -> dict: idempotent if is_nemotron_loaded() is false. If _nemotron_process is not None, sends signal.SIGINT, waits up to NEMOTRON_TERMINATE_GRACE_SECONDS, escalates to kill() if still running, sets _nemotron_process to None. Returns {"status": "unloaded"}.

stream_reply — signature (v8): stream_reply(message: str, history: Sequence[dict[str, str]] = (), endpoint_override: str | None = None, model: str | None = None) -> Iterator[StreamChunk]. New model parameter: when provided and truthy, it overrides the LLM_MODEL env var as the value of the "model" field in the upstream POST body. When endpoint_override is not None, the upstream POST target is endpoint_override; otherwise LLM_ENDPOINT is read from os.environ. When the upstream delta contains reasoning_content, yields ("think", reasoning_chunk) before any corresponding content token.

StreamChunk — unchanged tagged union: ("token", str), ("think", str), ("done",), ("error",).

SSE wire frames — extended: event: token (unchanged), event: done (unchanged), event: error (unchanged), plus new event: think — { "event": "literal 'think'", "content": "string" }.

Frontend behavior changes (v8):
- renderThink() splits on /(<think>|<\/think>)/ regex (restored from broken M5 coder output).
- processFrame handles event: think by wrapping payload content in <think> tags before appending to replyText, so the existing 💭 toggle renders them via renderThink().
- refreshModels() helper calls fetchModels() after successful load/unload API calls.
- load/unload button handlers call refreshModels() on success.

Configuration (read at request time — C-3, carried)

Env var | Default | M5 change
LLM_ENDPOINT | http://localhost:1234/v1/chat/completions | none
LLM_MODEL | local-model | fallback only when no model parameter passed to stream_reply
LLM_SYSTEM_PROMPT | `` (empty) | none
LLM_TIMEOUT_SECONDS | 120 | none

No new environment variables introduced.

Key flows
(unchanged from v7 — model list, Nemotron load/unload, chat routing, selector lock — see PRD for the walk-through.)

Constraints
M3 constraints C-1 through C-7, M4's C-8/C-9, and M5's C-10 (routing boundary lives in chat.py, stream_reply stays model-unaware beyond accepting the override and model parameter) and C-11 (no shared mutable state beyond _nemotron_process) all carry forward.

Oracle Mapping (AC → test node)
Carried from M3/M4 (unchanged). M5 tests re-authored for v8:

AC-1 → tests/test_models_service.py::test_list_models_includes_lmstudio_loaded_instances (unit) — tests/test_models_api.py::test_list_models_includes_lmstudio_loaded_instances (route)
AC-2 → tests/test_models_service.py::test_list_models_returns_empty_on_exception, test_list_models_returns_empty_on_non_2xx (unit) — tests/test_models_api.py::test_list_models_degrades_when_lmstudio_unreachable (route)
AC-3 → tests/test_models_service.py::test_list_models_omits_nemotron_when_not_loaded (unit) — tests/test_models_api.py::test_list_models_omits_nemotron_when_not_loaded (route)
AC-4 → tests/test_models_service.py::test_load_nemotron_spawns_and_confirms_ready (unit) — tests/test_models_api.py::test_load_nemotron_spawns_and_confirms_ready (route)
AC-5 → tests/test_models_service.py::test_load_nemotron_idempotent_when_already_loaded (unit) — tests/test_models_api.py::test_load_nemotron_idempotent_when_already_loaded (route)
AC-6 → tests/test_models_service.py::test_load_nemotron_timeout_clears_process_and_errors (unit) — tests/test_models_api.py::test_load_nemotron_timeout_returns_503_and_terminates (route)
AC-7 → tests/test_models_service.py::test_unload_nemotron_sends_sigint (unit) — tests/test_models_api.py::test_unload_nemotron_sends_sigint (route)
AC-8 → tests/test_models_service.py::test_unload_nemotron_idempotent_when_not_loaded (unit) — tests/test_models_api.py::test_unload_nemotron_idempotent_when_not_loaded (route)
AC-9 → tests/test_chat_model_routing.py::test_chat_routes_to_nemotron_and_passes_model (route)
AC-10 → tests/test_chat_model_routing.py::test_chat_routes_to_lmstudio_and_passes_model (route)
AC-11 → tests/test_chat_model_routing.py::test_chat_invalid_model_type_is_422 (route)
AC-12 → tests/test_chat_model_routing.py::test_chat_nemotron_selected_but_not_loaded_is_422 (route)
AC-18 → tests/test_llm_service.py::test_reasoning_content_yields_think_event (unit)

Milestone Justification (D-46)
Unchanged from v7 — one milestone, both features are prerequisites for one CEO-checkable selector.

Test dependencies
pytest, fastapi.testclient.TestClient, unittest.mock (for subprocess, httpx, and signal patching), pytest-httpserver, werkzeug, httpx.
