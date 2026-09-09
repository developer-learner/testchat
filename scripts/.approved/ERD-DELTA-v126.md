# ERD-DELTA v126 — T9 acceptance-only closeout

## Design

T9 implementation is complete at 3693f42. The final deterministic repairs
landed directly under D-132 after the coder failed, as recorded in
 tasks/T9-completion-review.md. All 237 frozen tests pass on both macOS and
sandbox. The six original T9 tests and all owner mappings remain unchanged.
This freeze declares the entire existing inventory acceptance-only so the
orchestrator verifies the outstanding mapped acceptance and records completion
without rebuilding already-verified files. No source edit is requested.
The carried empty-picker wording is Select model..., as required by AC-130.
Browser review also verified removal of stale modal handlers in chrome.js.

## Changed acceptance criteria

None. AC-183 through AC-188 and the carried regression suite remain binding.

## Superseded acceptance criteria

None.

## Changed files

- `src/static/catalog.js` — acceptance-only: the picker contract now records
  the already-tested compatibility behavior, exact-ID restore, carried AC-130
  placeholder, and unready marking for offline New Chat. No code is owed.

All inventoried files are explicit no_edit_files. The changed picker contract
invalidates its existing acceptance; it grants no new coder work.

## Coder briefs (verbatim)

No coder work is required. Preserve the implementation byte-for-byte and run
all existing mapped tests. In particular, retain the ready grouped options,
offline local default, source indicator, and removed lifecycle UI handlers.

## Task DAG

Preserve the validated task dependencies. Every task is acceptance-only.

## Test-to-file mapping

Retain all standing owner pins, including the six T9 tests. Do not move tests
away from their owners and do not drop any test from the milestone verdict.
