# ERD-DELTA v114 — router oracle made hermetic (test-isolation fix, no product change)

Freeze context: standing spec v113 (T3 chat.py gate restored to the accepted
implementation). The v113 milestone's mapped verdict was RED in the sandbox —
5 router tests failed — but NOT for any product defect. Root cause, proven by
bisection in the sandbox:

- `test_chat_router_model_router_down_is_422` called `httpserver.stop()` on
  the pytest-httpserver fixture. That underlying server is SESSION-SHARED
  across every httpserver-based test. Stopping it leaves a dead mock server
  for all later httpserver tests.
- When the mapped suite runs as sorted node-ids (the pipeline's invocation),
  this test sorts BEFORE the positive router tests, so their router probe
  (`httpx.get({VORTEX_URL}/v1/models)`) hits the dead server, returns empty,
  and `router_models()` yields `[]` — five assertions fail.
- Run as a whole file (definition order) the `stop()` test runs last, so the
  file passes 15/15 in isolation. Only the node-id verdict — exactly how the
  pipeline judges the milestone — exposes it. This is why T3 escalated: three
  coder attempts were told "the test fails, fix the code" when no product
  edit could fix a test that other tests break.

`src/api/chat.py` and `src/services/models.py` are correct and pass all 20
mapped tests once the one non-hermetic test is fixed (proven: 20/20 green in
the sandbox after the change below).

Fix: `test_chat_router_model_router_down_is_422` now simulates the router
being unreachable the way the suite already does elsewhere
(`test_router_models_empty_when_probe_raises`) — point `VORTEX_URL` at a dead
address and monkeypatch `models_mod.httpx.get` to raise `ConnectError` —
instead of tearing down the session-shared server. Same assertion (422), same
AC-173 behaviour, no shared-server teardown. No product file changes.

## Changed acceptance criteria

None. AC-170..AC-174 stand frozen since v107, unchanged. AC-173 (router-model
chat with the router unreachable is 422 pre-stream) is tested identically;
only the mechanism the test uses to make the router unreachable changes.

## Superseded acceptance criteria

None.

## Changed files

- `tests/test_router_route.py` (UPDATED: `test_chat_router_model_router_down_is_422`)
  — the single non-hermetic test rewritten to simulate router-down without
  stopping the session-shared httpserver.
- No product files change. `src/api/chat.py`, `src/services/models.py`, and
  every other source file are unchanged and already satisfy the corrected
  oracle.
- `scripts/.approved/contracts.json` — unchanged.

## Test-to-file mapping

* `tests/test_router_route.py::test_chat_router_model_router_down_is_422` (UPDATED)
  -> `src/api/chat.py`
