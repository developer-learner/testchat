ERD — testchat M5: Model Selection & Nemotron Runtime (erd_version 6)

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

ChatRequest — extended: { "message": str, "history": list[HistoryEntry] = [], "model": str | None = None }.
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
load_nemotron() -> dict: idempotent if already loaded; otherwise spawns via subprocess.Popen(["python3", expanded_script_path]) (expanduser applied before the call, not left to the OS), stores the handle in _nemotron_process, polls NEMOTRON_READY_URL via httpx.get in a loop up to NEMOTRON_READY_TIMEOUT_SECONDS; on success returns {"status": "loaded"}; on timeout, terminates the process, sets _nemotron_process back to None, returns {"status": "error", "message": ...}.
unload_nemotron() -> dict: idempotent if not loaded; otherwise calls _nemotron_process.terminate(), waits up to NEMOTRON_TERMINATE_GRACE_SECONDS, escalates to kill() if still running, sets _nemotron_process to None, returns {"status": "unloaded"}.

stream_reply — stream_reply(message: str, history: Sequence[dict[str, str]] = (), endpoint_override: str | None = None) -> Iterator[StreamChunk]. When endpoint_override is not None, the upstream POST target is endpoint_override; otherwise LLM_ENDPOINT is read from os.environ as in M3/M4 (C-3 carried).
StreamChunk — unchanged from M3/M4.
SSE wire frames — unchanged from M3/M4.

Configuration (read at request time — C-3, carried)
Env var | Default | M5 change
LLM_ENDPOINT | http://localhost:1234/v1/chat/completions | none
LLM_MODEL | local-model | none
LLM_SYSTEM_PROMPT | `` (empty) | none
LLM_TIMEOUT_SECONDS | 120 | none
No new environment variables introduced.

Key flows
(unchanged from prior M5 ERD revision — model list, Nemotron load/unload, chat routing, selector lock — see PRD for the walk-through.)

Constraints
M3 constraints C-1 through C-7, M4's C-8/C-9, and M5's C-10 (routing boundary lives in chat.py, stream_reply stays model-unaware beyond accepting the override) and C-11 (no shared mutable state beyond _nemotron_process) all carry forward unchanged.

Oracle Mapping (AC → test node)
Carried from M3/M4 (unchanged — see M4 ERD).

M5-specific (revised — service-level tests added so src/services/models.py has independent, file-scoped test coverage separate from src/api/models.py; route-level tests remain as integration confirmation of the wiring)

AC-1 → tests/test_models_service.py::test_list_models_includes_lmstudio_entries (unit) — tests/test_models_api.py::test_list_models_includes_lmstudio_entries (route, retained)
AC-2 → tests/test_models_service.py::test_list_models_returns_empty_on_exception, tests/test_models_service.py::test_list_models_returns_empty_on_non_2xx (unit) — tests/test_models_api.py::test_list_models_degrades_when_lmstudio_unreachable (route, retained)
AC-3 → tests/test_models_service.py::test_list_models_omits_nemotron_when_not_loaded (unit) — tests/test_models_api.py::test_list_models_omits_nemotron_when_not_loaded (route, retained)
AC-4 → tests/test_models_service.py::test_load_nemotron_spawns_and_confirms_ready (unit) — tests/test_models_api.py::test_load_nemotron_spawns_and_confirms_ready (route, retained)
AC-5 → tests/test_models_service.py::test_load_nemotron_idempotent_when_already_loaded (unit) — tests/test_models_api.py::test_load_nemotron_idempotent_when_already_loaded (route, retained)
AC-6 → tests/test_models_service.py::test_load_nemotron_timeout_clears_process_and_errors (unit) — tests/test_models_api.py::test_load_nemotron_timeout_returns_503_and_terminates (route, retained)
AC-7 → tests/test_models_service.py::test_unload_nemotron_terminates_process (unit) — tests/test_models_api.py::test_unload_nemotron_terminates_process (route, retained)
AC-8 → tests/test_models_service.py::test_unload_nemotron_idempotent_when_not_loaded (unit) — tests/test_models_api.py::test_unload_nemotron_idempotent_when_not_loaded (route, retained)
AC-9 through AC-12 → tests/test_chat_model_routing.py (unchanged — this pair, src/api/chat.py and src/services/llm.py, was never the file with the coverage gap)
AC-13 through AC-17 → CEO Demo Script (unchanged)

Milestone Justification (D-46)
Unchanged from prior revision — one milestone, both features are prerequisites for one CEO-checkable selector.

Test dependencies
pytest, fastapi.testclient.TestClient, unittest.mock (for subprocess and httpx patching), httpx.
