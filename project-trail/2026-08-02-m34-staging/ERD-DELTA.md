ERD Delta — testchat M34 additional local model deepseek-v4-flash-0731 (erd_version 74)

## Changed acceptance criteria

v74 adds AC-149 through AC-154. No prior AC is retired. AC-136 through
AC-148 (M33 conflict-safe history) and AC-111 through AC-135 (M31 + M32)
remain exactly as frozen. The new criteria concern only the additional
registry entry, its catalog projection, and its load/unload path parity
with existing script-model entries.

## Superseded acceptance criteria

None.

## Changed files

### `src/services/models.py`

Add five module-level constants sitting immediately below the pre-existing
`DEEPSEEK_*` block, in the same shape as that block:

```
DEEPSEEK_0731_BASE_URL = os.environ.get('DS4_0731_URL', 'http://127.0.0.1:8005')
DEEPSEEK_0731_CHAT_ENDPOINT = DEEPSEEK_0731_BASE_URL + '/v1/chat/completions'
DEEPSEEK_0731_READY_URL = DEEPSEEK_0731_BASE_URL + '/v1/models'
DEEPSEEK_0731_SCRIPT_PATH = '/Users/arc.elixir/dev/ds4/run-server-0731.sh'
DEEPSEEK_0731_READY_TIMEOUT_SECONDS = 300
```

Add one dictionary entry to `SCRIPT_MODELS`, keyed `deepseek-v4-flash-0731`,
whose shape MUST match the sibling `deepseek-v4-flash` entry exactly except
for values sourced from the new constants:

```
'deepseek-v4-flash-0731': {
    'id': 'deepseek-v4-flash-0731',
    'base_url': DEEPSEEK_0731_BASE_URL,
    'chat_endpoint': DEEPSEEK_0731_CHAT_ENDPOINT,
    'ready_url': DEEPSEEK_0731_READY_URL,
    'command': [DEEPSEEK_0731_SCRIPT_PATH],
    'ready_timeout_attr': 'DEEPSEEK_0731_READY_TIMEOUT_SECONDS',
},
```

No other module change. All existing constants, the `nemotron` entry, the
`deepseek-v4-flash` entry, the helper functions
(`_find_listening_pid`, `_terminate_pid`, `_responds_ready`,
`is_script_model_loaded`, `_unload_other_script_models`, `load_script_model`,
`unload_script_model`, `list_models`, `list_model_catalog`, etc.), the
back-compat `_nemotron_process` alias, and the `_reset_script_model_state`
lifecycle SHALL remain byte-identical.

The new entry is served by the same script-model machinery — RAM mutual
exclusion via `_unload_other_script_models` picks it up automatically because
that function iterates `SCRIPT_MODELS`; the load/unload API endpoints already
route by `{model_id}`; `list_model_catalog` already surfaces every
`SCRIPT_MODELS` entry.

### `src/api/models.py`

Extend both closed-set Literal unions to include the new source string. All
other fields, classes, response models, and route handlers SHALL remain
byte-identical.

```
class ModelInfo(BaseModel):
    id: str
    source: Literal["lmstudio", "nemotron", "deepseek-v4-flash", "deepseek-v4-flash-0731"]

...

class CatalogEntry(BaseModel):
    id: str
    source: Literal['nemotron', 'deepseek-v4-flash', 'deepseek-v4-flash-0731']
    loaded: bool
```

The order of Literal members matches the existing pattern (append at end).
Do not reorder pre-existing members.

## Test-to-file mapping

Backend nodes (both new tests target `src/services/models.py` first, then
`src/api/models.py` extends the schema surface):

* `tests/test_models_service.py::test_registry_contains_expected_script_models`
  (UPDATED existing test — set-equality now `{"nemotron", "deepseek-v4-flash", "deepseek-v4-flash-0731"}`;
  the existing assertions on the `deepseek-v4-flash` entry are unchanged and
  a parallel block asserts the new `deepseek-v4-flash-0731` entry's shape)
  → `src/services/models.py` (AC-149, AC-150, satisfied when the entry and
  constants are present).

* `tests/test_models_service.py::test_registry_0731_source_string_is_accepted_by_response_schema`
  (NEW test — instantiates `ModelInfo(id='x', source='deepseek-v4-flash-0731')`
  and `CatalogEntry(id='x', source='deepseek-v4-flash-0731', loaded=False)`
  and asserts no ValidationError) → `src/api/models.py` (AC-152).

Required DAG: `src/services/models.py` first; `src/api/models.py` depends on
it (the second test imports both modules, but the registry is source-of-truth
for the id string the schema must accept).

Existing tests untouched. `test_list_models_includes_deepseek_when_loaded`,
`test_load_evicts_a_running_untracked_other_model`, and other parametrized
tests keep their current parameter sets — extending them to cover the new id
is deliberately out of scope for this delta so the surface stays minimal
and the pipeline delta doesn't spiral.
