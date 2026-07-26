ERD — testchat M29: "unloaded" means unloaded (erd_version 58)

## What changes v57 -> v58

A behavior delta, not a ratify. One inventory file changes
(`src/services/models.py`); one may change if the coder chooses to surface the
new error path there (`src/api/models.py`). Both are already inventory members,
so no inventory growth.

The delta restates five process-lifecycle acceptance criteria in outcome form
(AC-102..AC-106, superseding AC-6/AC-7/AC-8/AC-95/AC-96) and re-cuts their
oracle against real subprocesses. See `PRD.md` for the criteria and for the
INV-1 provenance caveat that must be read before approving this freeze.

## Behavior newly locked

* **AC-102 — unload is defined by reachability, not by handle bookkeeping.**
  `unload_script_model` must leave the model's readiness endpoint unreachable
  whether or not `_script_processes` holds a handle for it. The untracked case
  is the one that matters: the handle map lives in module memory and does not
  survive a restart of the serving process, while a server spawned before the
  restart keeps running and keeps its port. Pinned by
  `test_models_service.py::test_unload_stops_a_running_server_with_no_tracked_handle`
  and `test_models_api.py::test_unload_route_stops_a_server_with_no_tracked_handle`.

* **AC-103 — unload can fail, and says so.** When the readiness endpoint stays
  reachable, the response is `{"status": "error", "message": ...}` naming the
  model. `ScriptModelUnloadResponse` and `NemotronUnloadResponse` already admit
  the `"error"` literal, so **no schema change is required**. Pinned by
  `test_unload_reports_error_when_the_model_stays_reachable` (service) and
  `test_unload_route_reports_error_when_the_model_stays_reachable` (route).

* **AC-104 — mutual exclusion is a state.** `_unload_other_script_models` (or
  whatever replaces it) must establish that the other model is unreachable
  before spawning, and must abort the load with an error naming the model it
  could not evict. Pinned by `test_load_evicts_a_running_untracked_other_model`
  and `test_load_refuses_when_the_other_model_cannot_be_evicted`.

* **AC-105 — a backing server that exits before readiness is not a timeout.**
  The wait loop already breaks on child exit; only the message is wrong. Pinned
  by `test_load_reports_child_exit_distinctly_from_the_deadline`.

* **AC-106 — a load that misses its deadline leaves nothing running.** The AC-6
  replacement, asserted as reachability rather than as a signal call. Pinned by
  `test_load_deadline_leaves_the_spawned_server_unreachable`.

## Implementation notes (non-binding — the tests are the contract)

The one genuinely new capability is reaching a server this process did not
spawn. Two in-tree precedents:

* `src/api/status.py::_script_model_rss_gb` already discovers a script model's
  PID by matching the launch command's basename when no handle is tracked. The
  same discovery satisfies AC-102.
* The registry entry's `base_url` carries the port, so port-based discovery is
  equally available.

Either is acceptable. Termination of a process this app does not own may need
escalation past SIGINT; the existing 5 s grace constant is unchanged, and
AC-103's error path is the specified outcome when termination is impossible.

**Do not** solve AC-102 by persisting handles to disk. The criterion is written
so that discovery, not memory, is the expected shape — a persisted PID is stale
in exactly the cases that matter.

## File inventory (M29 build) — UNCHANGED from v57

Same 12 files, same `no_edit_files` (markdown.js, rain.js, style.css). No task
adds an inventory member.

Files this delta expects to change:

* `src/services/models.py` — AC-102..AC-106 all land here.
* `src/api/models.py` — only if the coder routes AC-103's error through the
  route layer rather than returning it from the service. Either is acceptable;
  the route tests assert the response body, not where it was built.

## Oracle mapping

* `tests/test_models_service.py` — full replacement (24 tests). Maps to the
  `src/services/models.py` task.
* `tests/test_models_api.py` — full replacement (20 tests). Maps to the
  `src/api/models.py` task.

Both files previously asserted `send_signal` against `MagicMock` process
objects for every termination path. Those assertions are removed, not
weakened — a mock cannot fail to die, which is why the v57 suite was green
against a unload path that killed nothing. Mock-based tests are retained only
where the criterion is about a call being made (`spawn.assert_not_called()` for
load idempotence), never where it is about a resource reaching a state.

**New test-suite dependency:** these files spawn real short-lived Python HTTP
servers on ephemeral ports (`socket` bind-to-0), and guarantee teardown through
a fixture that kills survivors. No new package requirement — `socket`,
`subprocess`, and `sys` are stdlib. The sandbox must permit loopback TCP on
ephemeral ports; the existing UI suite already binds `APP_PORT` and the LLM
stub, so this is not a new capability.

## Smoke checks

Unchanged from v57.

## Rollback / risk

* Rollback is reverting `src/services/models.py` and re-freezing the v57
  oracle. The route contracts and response schemas are untouched either way.
* **Risk — killing a process this app did not spawn.** Discovery by command
  basename or by port could in principle match an unrelated process. Mitigation
  is that both script models launch from absolute, project-specific paths
  (`/Users/arc.elixir/dev/ds4/run-server.sh`, `~/nemotron-vmlx.py`) and bind
  fixed loopback ports. Accepted; the alternative is the current defect.
* **Risk — AC-103 turns a previously silent success into a visible error.** A
  user who unloads a model the app genuinely cannot kill now sees an error
  instead of a false success. That is the point, but it is a user-visible
  behavior change worth naming at UAT.
* **Risk — real-subprocess tests are slower and can flake** on a loaded machine
  (the AC-42 precedent). Timeouts are set at 10 s with polling rather than
  fixed sleeps, and every wait is a predicate loop, so the failure mode is a
  clear assertion rather than a race.

## CEO acceptance (D-44)

Observable without reading code:

1. Conductor starts the app and loads DeepSeek from the dropdown.
2. Conductor restarts the app (any way — a file save is enough).
3. CEO clicks Unload.
4. **Expected:** the model actually stops — the dropdown shows it unloaded, and
   the conductor can show that nothing is listening on the model's port.
   Before this delta, step 4 reported success and the model kept running.
