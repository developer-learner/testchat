# ERD-DELTA v103 — provenance-only test docstring correction

Standing spec: v102. This delta corrects a fabricated provenance note in
`tests/test_model_lifecycle.py` (the v101/v102 re-freeze retune clauses were
baked into the docstring at `7bfc622` authorship but no such byte change ever
landed in the file). No behavior, contracts, or AC semantics change.

## Changed acceptance criteria

None — v103 is a docstring-only correction. Sentinels unchanged.

## Superseded acceptance criteria

None.

## Changed files

- `tests/test_model_lifecycle.py` — docstring only (provenance correction);
  no test body change. `SRC_CHANGED_FILES`: none.

## Test-to-file mapping

* `tests/test_model_lifecycle.py::test_concurrent_loads_spawn_at_most_one_server`
  -> `src/services/models.py`