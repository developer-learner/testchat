ERD Delta — testchat M34: additional local model deepseek-v4-flash-0731 (spec v79)

## Changed acceptance criteria

v79 introduces AC-149, AC-150, and AC-151. No prior acceptance criterion
changes in meaning; AC-111 through AC-148 remain exactly as frozen. The new
criteria concern only the third script-model registry entry
(`deepseek-v4-flash-0731`), its default endpoints and `DS4_0731_URL`
environment override, and the response-schema `source` value that lets the
model list surface it.

## Superseded acceptance criteria

None. This milestone is purely additive: a third entry alongside `nemotron`
and `deepseek-v4-flash`, with no change to their behavior, ports, or the
shared load / unload / RAM-mutual-exclusion machinery.

## Changed files

### `src/services/models.py`

Add a `DEEPSEEK_0731_*` constant block immediately below the existing
`DEEPSEEK_*` block, all module-level and read at import, in the same shape:

    DEEPSEEK_0731_BASE_URL = os.environ.get('DS4_0731_URL', 'http://127.0.0.1:8005')
    DEEPSEEK_0731_CHAT_ENDPOINT = DEEPSEEK_0731_BASE_URL + '/v1/chat/completions'
    DEEPSEEK_0731_READY_URL = DEEPSEEK_0731_BASE_URL + '/v1/models'
    DEEPSEEK_0731_SCRIPT_PATH = '/Users/arc.elixir/dev/ds4/run-server-0731.sh'
    DEEPSEEK_0731_READY_TIMEOUT_SECONDS = 300

`os` is already imported at module top. Then add exactly one entry to the
`SCRIPT_MODELS` dict, keyed `deepseek-v4-flash-0731`, shaped identically to the
sibling `deepseek-v4-flash` entry but sourced from the new constants:

    'deepseek-v4-flash-0731': {
        'id': 'deepseek-v4-flash-0731',
        'base_url': DEEPSEEK_0731_BASE_URL,
        'chat_endpoint': DEEPSEEK_0731_CHAT_ENDPOINT,
        'ready_url': DEEPSEEK_0731_READY_URL,
        'command': [DEEPSEEK_0731_SCRIPT_PATH],
        'ready_timeout_attr': 'DEEPSEEK_0731_READY_TIMEOUT_SECONDS',
    },

No other line in the module changes: the `nemotron` and `deepseek-v4-flash`
entries, every existing constant, the helper functions (`_find_listening_pid`,
`_terminate_pid`, `load_script_model`, `unload_script_model`,
`is_script_model_loaded`, `_unload_other_script_models`, `list_models`,
`list_model_catalog`, `get_script_model`), the `_nemotron_process` back-compat
alias, and the process-state dict remain byte-identical. The new entry needs no
new function: `_unload_other_script_models`, the load/unload endpoints, and
`list_model_catalog` already iterate or route over `SCRIPT_MODELS` and pick it
up automatically.

### `src/api/models.py`

Append the string `"deepseek-v4-flash-0731"` as the final member of two closed
`Literal` unions (`Literal` is already imported from `typing`); append at the
end, do not reorder existing members:

    class ModelInfo(BaseModel):
        id: str
        source: Literal["lmstudio", "nemotron", "deepseek-v4-flash", "deepseek-v4-flash-0731"]

    class CatalogEntry(BaseModel):
        id: str
        source: Literal['nemotron', 'deepseek-v4-flash', 'deepseek-v4-flash-0731']
        loaded: bool

`ModelInfo` and `CatalogEntry` are pydantic `BaseModel`s from
`src/api/models.py`; widening a `Literal` only enlarges the accepted `source`
set and changes nothing else. All other classes, response models, routes, and
the two back-compat aliases (`NemotronLoadResponse`, `NemotronUnloadResponse`)
remain byte-identical.

## Test-to-file mapping

Both tests live in `tests/test_models_service.py`; it imports the registry as
`src.services.models` and the schemas as `from src.api.models import ModelInfo,
CatalogEntry`.

- `test_registry_contains_expected_script_models` (UPDATED existing test) —
  set-equality now `{"nemotron", "deepseek-v4-flash", "deepseek-v4-flash-0731"}`;
  the existing `deepseek-v4-flash` assertions are unchanged, and a parallel
  block asserts the new entry's `command`, its `chat_endpoint`/`ready_url`
  suffixes, and its `base_url` default. Pins **AC-149** and **AC-150** against
  `src/services/models.py` — build this file first.

- `test_registry_0731_source_string_is_accepted_by_response_schema` (NEW test)
  — constructs `ModelInfo(id="x", source="deepseek-v4-flash-0731")` and
  `CatalogEntry(id="x", source="deepseek-v4-flash-0731", loaded=False)` and
  asserts neither raises `pydantic.ValidationError`. Pins **AC-151** against
  `src/api/models.py`.

Required DAG: `src/services/models.py` first (source of truth for the id
string), then `src/api/models.py` (its schema must accept that id). The
existing parametrized load / unload / eviction oracles are intentionally left
covering the current entries only; extending them to the new id is out of scope
so the delta stays minimal.
