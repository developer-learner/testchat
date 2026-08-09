# ERD-DELTA — spec v88: conversation data safety

This milestone repairs the three persistence defects identified in the
2026-08-08 audit. It is intentionally limited to exact-one deletion,
recoverable initial hydration, and quarantine of schema-invalid JSON. Model
lifecycle, process ownership, CSRF, source-URL validation, settings UX,
documentation drift, and accessibility findings remain outside this slice.

## Changed acceptance criteria

* **AC-156 — exact-one deletion:** confirming one row deletion removes only
  that thread and persists the complete survivor snapshot, such that reload
  returns all and only the survivors.
* **AC-157 — mutation verb boundary:** a row deletion uses the revisioned PUT
  queue and never the clear-all DELETE route, such that survivors cannot be
  replaced by an empty snapshot.
* **AC-158 — hydration failure visibility and retry:** a failed initial GET
  must write exactly `history unavailable — retrying` to `history-status`,
  retry automatically, and create no replacement state while revision is
  unknown.
* **AC-159 — hydration recovery:** a successful retry installs threads and
  revision before later writes and clears the warning, such that the next
  mutation and all survivors persist through reload.
* **AC-160 — schema-invalid quarantine:** valid JSON whose thread/message
  shape fails the PUT `ThreadSnapshot` model is quarantined byte-for-byte and
  read as empty zero, such that invalid state is neither served nor
  overwritten.

## Superseded acceptance criteria

None. AC-142 remains the contract for explicit clear-all, such that its
revision-precondition and empty-snapshot semantics are unchanged.
The standing unreadable-snapshot quarantine and backup-visibility behavior
remains unchanged. AC-156..160 close previously unpinned paths without
weakening those behaviors.

## Changed files

* `src/static/threads.js` — AC-156/157/158: post-delete survivors are
  enqueued via the ordered revisioned PUT; never DELETE `/api/v1/threads`;
  hydration alone owns `history-status`.
* `src/static/app.js` — AC-158/159: on failed GET write exact text and
  retry until success; a success installs threads + revision before mutation;
  later PUTs adopt response revision.
* `src/services/storage.py` — AC-160: under lock, an optional validator
  moves JSON/shape failure to `<primary>.corrupt-<timestamp>` and returns
  `([], 0)`; backup/revision semantics unchanged.
* `src/api/threads.py` — AC-160: GET passes a `ThreadSnapshot` based
  validator to storage; quarantine reads yield `{threads: [], revision: 0,
  quarantined: true}`, such that invalid state is neither served nor
  overwritten.

DAG: `src/api/threads.py` depends on `src/services/storage.py`; the two
browser files are orderable but app.js acceptance assumes threads.js
hydration-status ownership.

## Test-to-file mapping

No v88 `contracts.test_mapping` keys: D-107 allows pinning known node-IDs
only. Browser tests get D-64 placement; the EM must place the quarantine
node-id test downstream of storage, at the threads API task. After v88
collects those node-IDs, the follow-up freeze pins:
backend (storage) [node test] -> `src/api/threads.py`;
browser delete-test -> `src/static/threads.js`;
browser hydration-test -> `src/static/app.js`.
No existing test is changed; the three delta tests are red against the v87
tree (D-75); no new route, DOM surface, or external capture is added.
=== END FILE ===
