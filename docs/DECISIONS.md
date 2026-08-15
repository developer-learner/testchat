# DECISIONS.md — Architectural Decision Log

> Every non-obvious technical decision goes here with the reasoning.
> This prevents the LLM from "helpfully" undoing choices you already made.
> Format: date, decision, why, what not to suggest.

---

## Template

```
## YYYY-MM-DD — [Decision title]

**Decision:** [What was decided]
**Alternatives considered:** [What else was evaluated]
**Reason:** [Why this choice was made]
**Do not suggest:** [What the LLM should not propose as a "fix"]
```

---

## Decisions

## D-149 — 2026-08-14 — check-spec-delta's test_mapping pin gate family-matches node-ids (D-116/D-124)

**Decision:** The `check-spec-delta.py` pin gate no longer compares `contracts.test_mapping` keys to frozen `test-nodeids` by raw string equality. Both sides are reduced to the D-116/D-124 node-id family (module-prefix + bare test name, parametrization suffix stripped via the same `_node_family` rule `validate-plan.py`'s `_id_family` uses) before membership testing, so a mapping key of either shape — `name[chromium]` or `name` — satisfies a frozen node-id of the other. The "unknown node-id" rejection still fires for a key whose family is genuinely not frozen (testchat v106 froze `test-nodeids` in bare form while `contracts.json` kept the three `[chromium]`-suffixed keys, and select-2 transport was already family-tolerant; remaining tolerance asymmetry was a latent false-positive trap at the next real freeze).

**Alternatives considered:** (a) Data-side only: normalize the two frozen `test_mapping` keys in `contracts.json` to bare form — rejected as the sole fix because the collection shape flips both ways between freezes (D-116 selftests pin `_FLICKER_OLD`/`_FLICKER_NEW` in both directions), so a one-time rewrite would break again at the next environment flip; the gate, not the data, is the recurring failure mode. (b) Gate tolerance only, keeping the frozen mapping suffixed — accepted (family matching on both sides is symmetric and matches the file's own DELTA-token handling at ~line 151).

**Reason:** The pin gate existed to stop a mapping key that is not a frozen node-id (M35b class — a gate cannot honor placement for a test that does not exist). Exact-match satisfied that intent when collection shape was stable, but D-116/D-124 explicitly bless `name[chromium]` and `name` as the same test, and the family-match already governs every other consumer (`_id_family` in `validate-plan.py`, the D-116 flicker guard, DELTA-token matching). A gate that rejects a key the rest of the control plane treats as identical is a self-inflicted hard block on the next behavioral freeze over an already-consistent frozen state.

**Do not suggest:** reverting the pin gate to exact string equality; "repairing" the frozen `test_mapping` keys to silicon-bare form as a substitute for gate tolerance (they denote the same family); weakening the unknown-family rejection to allow arbitrary suffixed keys; deleting the two direction-pinned selftests. Cross-repo: derived projects receive the gate, the two selftests, manifest re-pins, and this ledger entry through the same propagation batch.

## D-148 — 2026-08-14 — Historical PRD acceptance-criterion blocks are immutable and contiguous

**Decision:** The D-136 PRD additive guard preserves each historical acceptance criterion as a complete Markdown block, not merely as an identifier. `check-prd-additive.py` recognizes AC bullet/heading starts, delimits each block at the next AC or section heading, normalizes whitespace so harmless line wrapping remains possible, and fails closed when a historical block is missing, duplicated, altered, or split by an interleaved criterion. New AC blocks remain additive and may be placed between existing complete blocks. Supersession remains an ERD-DELTA operation that retains the historical PRD block.

**Alternatives considered:** (a) Continue checking only the set of AC ids — rejected because a staged PRD can retain every id while rewriting behavior or inserting a new criterion inside an old body. (b) Require raw byte identity — rejected because Markdown line wrapping does not change the criterion and full-file TPM returns may reflow prose. (c) Repair malformed records without strengthening the gate — rejected because the next full-file return could recreate the same corruption undetected.

**Reason:** Testchat's standing PRD retained the names AC-160, AC-166, and AC-167 but interleaved their bodies: two new AC starts split AC-160, while the trailing bodies of AC-166 and AC-160 became part of AC-167's apparent block. The id-set guard returned green because all three names survived. D-147 now sends this complete accumulated PRD to every TPM intake, so structural corruption can directly misstate historical product behavior. Block-level preservation closes the exact seam while retaining additive authoring and whitespace-only reflow.

**Do not suggest:** weakening preservation back to id presence; allowing historical body edits because the id remains; treating duplicate AC starts as harmless; making whitespace layout byte-identical; silently repairing a malformed frozen PRD outside `refreeze.sh`. Cross-repo: derived projects receive the guard and selftests through template sync, but an already-malformed project PRD must be repaired through one legitimate refreeze before installing this stricter guard.

## D-147 — 2026-08-14 — Trim no-delta ERD context, but always ship the full PRD (amends D-117; corrected same day)

**Decision:** `tpm-pack.sh` always emits the complete frozen `PRD.md`, whether or not an `ERD-DELTA.md` is active. A staged PRD is a complete additive replacement under D-136, and the chat TPM must see every historical AC id it is required to preserve or supersede. The no-delta optimization applies only to the standing ERD: the generated standing summary replaces full `ERD.md`, while the complete interface index and TPM-requested stage-2 contract bodies remain available. Missing summary generation or relative expansion retains D-117/D-145's loud full-ERD fallback.

**Alternatives considered:** (a) Keep the PRD capsule and add on-demand PRD retrieval — rejected as premature machinery to save about 25 KB without measured context pressure; unlike contracts, no PRD section protocol or mechanical merge exists. (b) Keep the capsule with no retrieval path — rejected because it makes the D-136 additive guard impossible for a chat TPM to satisfy safely. (c) Restore both full PRD and full ERD — rejected because the ERD summary plus current delta and requested contract bodies retain a working scoped path.

**Reason:** The original D-147 treated the PRD and ERD as symmetric trims. They are not: stage 2 retrieves contract bodies only, while no path can recover omitted PRD acceptance criteria. Testchat's packed PRD block fell to 576 bytes and zero AC ids while the standing PRD held 55 ids required by the additive guard. Restoring roughly 25 KB of non-scarce frontier context removes a latent hard failure; the measured ERD saving remains.

**Do not suggest:** reintroducing a PRD capsule without a real PRD retrieval-and-merge mechanism backed by measured context pressure; weakening the additive guard to accommodate missing input; restoring the full standing ERD merely because the PRD is full; dropping the full-ERD fallback on summary failure. Cross-repo: derived projects receive the packer and selftests through template sync and align this corrected entry in the same propagation batch.

## D-146 — 2026-08-14 — Milestone cutting optimizes the shortest safe route, not just error containment; close-out records time spent (amends D-46)

**Decision:** TPM guidance (docs/TPM-ROLE.md, "Milestone sizing") is extended with a milestone-cutting rule and a PRD scope brief. Cutting is no longer framed only as error-containment vs cycle-overhead balance (small enough to fail cheaply, big enough to avoid trivia): the TPM is directed to prefer the shortest safe route to the business outcome. Choose the smallest coherent, CEO-checkable outcome (D-44) that moves the product forward; include work only when it directly delivers that outcome, is required for its correctness or safety, or is an unavoidable dependency on the outcome's critical path; defer unrelated cleanup, speculative generalization, optional polish, and future-proofing; prefer the task order that minimizes elapsed time and rework; record what was deliberately excluded. This is TPM judgment — no new gate, no numeric formula. The PRD's scope brief states briefly: intended outcome, essential scope, explicitly deferred scope, why each task is necessary, and an expected time band; close-out records the actual elapsed time and avoidable rework (the per-milestone feedback loop).

**Alternatives considered:** (a) A hard gate / numeric target on milestone time or task count — rejected: variance across projects is the point of D-46, and a numeric formula would force recuts that burn the very cycles sizing exists to avoid; the operator who owns the trade-off is the TPM, not a threshold. (b) Leave TPM-ROLE.md unchanged, trusting "justify the cut briefly in the PRD" — rejected: the prior text optimized error containment but never stated the relevance/critical-path commitment, so a spec could pass "small/big" sizing while shipping speculative or out-of-scope work, and nothing required a time-band estimate or close-out measurement. (c) A separate PRD template section enforced at freeze — rejected: this is guidance for the authoring seat, not frozen-spec structure to gate; the fields are stated in TPM-ROLE.md and it is the TPM's judgment to weigh them.

**Reason:** Post-ship review of time efficiency: the control plane is already substantially trimmed (20-minute anti-thrash budget; delta-mapped verdict scope instead of a 45–60-minute full suite; mechanical plan transcription replacing a 45–90-minute EM planning call; D-93 small-change bypass; parsimony-governed tests; D-46 sizing). The identified gap is that TPM guidance optimized error containment versus cycle overhead but did not explicitly require the shortest safe route to the business outcome. This decision makes that the stated primary, alongside the D-126 metrics-report defect fix (the success path passed `v$FROZEN_V`, which the reporter's `int()` rejected and `|| true` swallowed — no `metrics.tsv` row) that restores the per-milestone feedback loop.

**Do not suggest:** turning the rule into a hard gate, numeric target, or frozen PRD schema; removing the close-out time/rework recording once the metrics loop returns; weighing speculative generalization as in-scope; a milestone with no CEO-checkable outcome "to keep momentum."

## D-145 — 2026-08-14 — Context byte budgets warn on growth; generated slices may never exceed their sources

**Decision:** Model-facing context has five pinned warning budgets, measured in exact UTF-8/file bytes by `scripts/context-budget.py`: TPM stage-1 bundle 88,000; standing summary 8,192; complete interface index 16,384; assembled EM package 65,536; escalation shared-context block 32,768. Absolute overruns warn on stderr and continue—the safe full-artifact fallback and a genuinely large active delta remain available. Relative expansion is a hard generator rejection: every pack-produced role, schema, standing-summary, ERD-delta, interface-index, and requested-contract-body slice must be no larger than its source artifact. A rejected slice enters the existing loud full-source fallback. `contracts-delta.py` enforces the same invariant when called outside `tpm-pack.sh`. The EM measurement is the exact saved user prompt plus its system prompt and response schema; escalation measures the exact shared block emitted once at the batch top. The product-capsule budget was retired with D-147's same-day correction because the PRD is no longer sliced.

**Alternatives considered:** (a) Hard-fail every absolute overrun—rejected because a warning budget is a regression signal, while a safe fallback may intentionally be larger and must not disappear when context generation fails. (b) Measure only the whole TPM bundle—rejected because a stable total can hide one component expanding while another shrinks, and it leaves EM/escalation growth invisible. (c) Test only current testchat artifact sizes—rejected because the blueprint serves projects of different legitimate sizes; runtime warnings plus pinned synthetic boundary tests preserve the signal without baking one child's content into the template. (d) Assume minification guarantees shrinkage—rejected because an already-compact or tiny source can make generated index/scaffolding larger; compare actual bytes.

**Reason:** Context trimming had point-in-time size evidence but no durable regression boundary. A later prompt, schema, interface family, or shared-context edit could silently restore whole-app load while every semantic selftest stayed green. Per-surface budgets identify which layer grew, and the no-expansion invariant makes “slice” a mechanically true claim rather than a naming convention.

**Do not suggest:** suppressing an over-budget warning without either trimming the surface or deliberately revising this decision and its pinned test; converting absolute warnings into hard halts without a CEO policy decision; accepting a generated slice larger than its source because it is structurally cleaner; counting only line totals or approximate tokens when exact bytes are available; dropping the full-source fallback on slice rejection. Cross-repo: derived projects receive the tool, call-site wiring, selftests, and manifest pins through template sync and align this ledger entry in the same propagation batch.

## D-144 — 2026-08-14 — Stage-1 pack names the active build inventory; contracts-delta's default never reapplies the standing slice (amends D-140/D-141)

**Decision:** `scripts/contracts-delta.py` body mode, when `SWBP_CONTRACT_FILES` is absent, no longer silently defaults to the standing accumulated `contracts.files`. Its standalone inventory source is D-140-ordered: the newest modern DELTA snapshot (one carrying `inventory_files`) beside the contracts file is authoritative and may be empty (a consolidation keeps no standing pin); an all-legacy or absent snapshot retains the historical `contracts.files` behavior; a malformed modern snapshot fails closed (exit 1 → the shell falls back to the full contracts file loudly). Separately, `tpm-pack.sh` stage 1 now notes the executor's active build inventory (D-140) below the COMPLETE interface index (D-141) — a consolidation prints "none — <snapshot> is a consolidation", and an active snapshot names its files — so the next feature is authored against active scope rather than the standing or previous-milestone list.

**Alternatives considered:** (a) Fix nothing — rejected: the live pack already emits the D-141 index and the EM lane already sets `SWBP_CONTRACT_FILES`, so the standing default was latent dead code, but any future caller that forgot the env would silently re-slice the accumulated surface — the exact D-140 "do not suggest" pin, with no failure. (b) Make stage-2 `--contracts-for` select files from the EM's active inventory — rejected: D-141 forbids it (author's scope, not the executor's) and the index is deliberately scope-free. (c) Delegate the standalone default to `validate-plan.py --active-inventory` — rejected: that command reads the module-level `CONTRACTS` constant, not the producer's argument, so the parser tests would diverge; the newest-snapshot rule is self-contained and can never reintroduce standing surface. (d) Show only the index with no active-inventory note — rejected on purpose: the note is what makes pack preparation truthful for the next feature (the D-140 narrow vs the accumulated complete).

**Reason:** Pending item 1 of the post-ship audit — "TPM-pack contract selection still slices contracts using the previous standing inventory" — did not reproduce in the pack flow (stage-1 is the D-141 complete index, stage-2 is TPM-named, the execution lane is D-140-scoped at `orchestrate.sh` lines 658–684). The real residual was the producer's env-absent default: `contracts-delta.py` returned to `contracts.files` whenever the env was missing, which D-140's "Do not suggest" pin names directly. This amendment makes that pin structural and adds the informational active-inventory line so pack preparation shows active scope.

**Do not suggest:** reverting the body-mode default to the standing `contracts.files` when a modern snapshot is available; selecting stage-2 files from the active inventory at pack time (D-141); emitting contract bodies into the index note; treating the active-inventory note as making the (still complete) index authoritative for build scope. Cross-repo: derived projects receive the code and selftests via template sync and must align this ledger entry in the same propagation batch.

## D-143 — 2026-08-14 — Retire the S7 ERD-section-size advisory (D-85)

**Decision:** The freeze-time S7 advisory (an ERD section exceeding 1200 chars would warn that downstream plan briefs might exceed `MAX_BRIEF_CHARS`) is retired and removed from `refreeze.sh`. Its absence is now pinned by an inverted selftest. This is the D-85 selection rule applied: a paid freeze-time advisory that has produced no behavioral change is retired rather than kept to demonstrate diligence.

**Alternatives considered:** (a) Keep S7 as a soft early signal — rejected: it predicts exactly what the plan gate enforces harder (mass rejection over `MAX_BRIEF_CHARS`), so it can never act before the gate with information the gate lacks; the D-89 class was retired in the same ledger for the same "duplicated the plan gate's already-harder check" reason. (b) Lower S7's threshold to act earlier — rejected: a threshold that fires on every real freeze is noise, not signal, and the plan gate remains the enforcement point either way.

**Reason:** S7 never blocked a freeze (advisory by construction) and has no documented behavioral change in its track record — the v105 consolidation freeze printed it to a verdict nobody consumed. D-56 (undeclared-externals heuristic, caught the v8/v9 class) and D-80 (D-68 debt sweep, forced the M28 v54 recut and remediation directives) are retained: both have demonstrated blast radius exceeding their runtime cost. The plan gate's `MAX_BRIEF_CHARS` rejection remains the hard, authoritative check.

**Do not suggest:** reintroducing an ERD section-size advisory at freeze time; moving S7 lower/higher rather than deleting it; making the plan-gate brief check an advisory (it stays a hard halt — the EM cannot act on a soft signal); treating D-56/D-80 as equally retired without their behavioral-change evidence.

## D-142 — 2026-08-14 — Reuse mypy green verdicts only for an identical typing fingerprint

**Decision:** `run_tests` stores a successful mypy verdict in the current milestone's ephemeral `.pipeline-state/mypy-green/` directory, keyed by a SHA-256 fingerprint of the exact mypy target list plus every `src/**/*.py` file and the repository inputs that determine type-check behavior: mypy/config files, dependency manifests and locks, `Containerfile`, `scripts/sandbox-run.sh`, `MYPYPATH`, and `MYPY_CONFIG_FILE`. A matching marker skips only mypy; pytest still runs for every acceptance/verdict invocation. Mypy failures are never cached. Scoped and whole-tree target sets have distinct fingerprints, and any fingerprinting or marker-write failure halts rather than using an unknown result.

**Alternatives considered:** (a) Run mypy once per milestone — rejected because later coder tasks may change Python sources or their dependencies. (b) Cache failures too — rejected because a retry may repair the environment or source and must receive a fresh verdict. (c) Hash only the explicitly targeted files — rejected because mypy follows imports and is also controlled by configuration, dependencies, and its sandbox image. (d) Persist the cache outside `.pipeline-state` — rejected because reuse is needed only across repeated checks in one active milestone; cross-run reuse adds stale-environment risk for little benefit.

**Reason:** The orchestrator invokes the same acceptance funnel after individual tasks, retries, isolation probes, and the final regression pass. When neither the checked target set nor any typing input changed, rebuilding the sandbox and repeating mypy proves no new fact. Fingerprinting the conservative full Python source closure removes that repeated cost without weakening task-scoped checks, the final whole-tree check, or pytest execution.

**Do not suggest:** reusing a green marker after any Python/config/dependency/sandbox input changes; caching a nonzero or missing mypy result; treating a scoped marker as proof for `mypy src/`; skipping pytest because mypy was cached; making the cache tracked or durable across completed milestones. Cross-repo: derived projects receive the script, selftest, and manifest pin through template sync and must align this ledger entry in the same propagation batch.

## D-141 — 2026-08-14 — TPM intake is two-stage: a complete interface index first, bodies only for files named after intent

**Decision:** `tpm-pack.sh` ships, as the contracts block of the stage-1 bundle, a COMPLETE compact interface index generated by `scripts/contracts-delta.py --index`: every entry point, route (method/path), schema (field NAMES only), error (status), and ui id (testid) in the accumulated spec. Entry points are plain ids (they self-pin — the module is derivable from `src.pkg.mod:obj`). The pinned families are grouped by owning file under a `by_file` map, with `(unpinned)` collating every entry whose pin is missing (so an unpinned interface is still always carried in body mode). Full contract bodies arrive only in a stage-2 follow-up (`tpm-pack.sh --contracts-for <file> [<file>...]`) for exactly the files the TPM names after hearing the new feature's intent. The standing accumulated contracts artifact is never shipped whole to the TPM lane in either stage.

**Alternatives considered:** (a) Keep slicing bodies by the previous milestone's `contracts.files` — rejected: the slice was context from the prior feature, and it hid 27/35 entry points, 12/15 routes, 14/21 schemas, and 3/5 errors from the seat that authors the next contracts delta (board finding 3); (b) ship the full accumulated contracts.json — rejected outright (the accumulated artifact grows without bound; it is exactly what D-120's slice exists to keep out of context); (c) slice bodies by the CURRENT active milestone inventory — rejected: the TPM's next feature is unknown at pack time, so any file-based body selection is still stale scope; only an index is scope-free.

**Reason:** The TPM cannot state which files it needs until it hears the feature intent; body selection therefore belongs after the intent statement, in the CEO relay loop. An index with pins gives complete visibility (nothing hidden, no silent drop — D-120's no-silent-drop becomes the index's completeness invariant) at ~7.2 KB after the by-file compaction — grouping the pinned families under their owning-file keys writes each path once instead of on every entry, cutting the index from ~10.6 KB (a further ~32%) with zero interfaces dropped, while still covering 100% of interfaces (vs 8/35 entry points, 3/15 routes, 7/21 schemas, 2/5 errors visible to the TPM before). Bodies are on demand, so the seat authors deltas against the actual shapes of exactly the files it will touch.

**Do not suggest:** restoring the previous-milestone file slice or the full accumulated artifact to stage 1; putting bodies back in the index to "save a round trip"; selecting stage-2 files from the EM's active inventory at pack time (that is the executor's scope, not the author's); removing the `(unpinned)` marker.

## D-140 — 2026-08-14 — Active milestones carry exact work, per-freeze instructions, and runnable test scope

**Decision:** A freeze records three independent facts in `DELTA-vN.json`: `inventory_files` is the exact build inventory snapshot and may be empty; `changed_tests` contains only living runnable tests whose executable function AST changed; `retired_tests` contains removed node-ids for invalidation only. A test function's leading docstring, comments, whitespace, and formatting are nonbehavioral and do not enter `changed_tests`. The MODULE docstring is likewise nonbehavioral: an edit confined to it scopes nothing instead of tripping the file-level fallback (the v103 class — one docstring edit re-ran five model-lifecycle tests). `refreeze.sh` also preserves the staged instruction slice as hash-pinned `ERD-DELTA-vN.md`. D-113's active milestone is the ordered union of its per-freeze inventories and instruction snapshots, not the newest `contracts.files`/`ERD-DELTA.md`. The contract-body slice, mechanical synthesis, fallback EM prompt, validation, and node-id scope all consume that same active set. An active set with no inventory, changed contracts, or runnable tests produces and validates `tasks: []`; no EM or coder is invoked.

**Alternatives considered:** (a) Keep `contracts.files` non-empty and manufacture no-edit tasks — rejected because documentation-only and retirement freezes then re-plan accumulated files that have no behavioral work. (b) Keep one mutable `ERD-DELTA.md` and trust the newest freeze to restate skipped work — rejected because v100-v102 instructions disappeared when v103 overwrote the file. (c) Keep removed ids in `changed_tests` and filter only at execution — rejected because the mixed channel still pollutes planning and prompt scope. (d) Treat every test-function byte change as behavior — rejected because docstring-only edits created runnable work with no executable delta.

**Reason:** The control plane's safety model already preserves every JSON DELTA since the last success, but its plan inputs did not represent the same range: the current inventory could retain historical files, the current ERD delta erased earlier instructions, and the changed-test list mixed runnable, retired, and documentation-only ids. The split makes milestone scope both smaller and more truthful. Modern freezes are self-contained through immutable snapshots. During migration, all-legacy ranges preserve their historical contracts.files behavior; mixed ranges use legacy `changed_files`/changed-contract owners without reintroducing accumulated inventory. Pre-D-140 instruction slices are recovered from the Git commit that introduced their DELTA when possible; synthetic/pre-Git legacy fixtures retain the current-file fallback, while a modern missing snapshot fails closed.

**Do not suggest:** requiring a placeholder file/task for an empty milestone; feeding retired node-ids to pytest or the EM; restoring raw source-byte comparison for test functions; using only the newest ERD-DELTA in a skipped-freeze range; slicing contracts against standing `contracts.files` when the active inventory is available; silently skipping a missing modern `ERD-DELTA-vN.md`. Cross-repo: derived projects receive code/schema/selftests through template sync and must align this ledger entry in the same propagation batch.

## D-139 — 2026-08-14 — TPM and milestone runs are CEO-gated at launch: inform first, ask who takes the TPM seat

**Decision:** When an LLM agent concludes that a fix needs a TPM round-trip or a milestone (orchestrate) run, it SHALL inform the CEO and ask before launching — never run straight into packing a TPM bundle, starting a milestone, or assuming a TPM session is pending. When a TPM is needed, the agent SHALL ask who will take the role: the same LLM may take it (a conductor may also hold the TPM seat, by explicit CEO assignment), or another LLM may — the TPM is a seat, not a fixed external party. The default `scripts/tpm-pack.sh`/`tpm-agent.sh` paths remain valid once the CEO names the holder. No agent assumes "the TPM is someone else" or that a TPM/milestone-based fix runs automatically.

**Alternatives considered:** (a) keep the existing implicit flow (agent detects TPM needed → packs bundle → relays to the presumed web-chat TPM) — rejected: exactly the assumption this session's fix hit, and the CEO directed it removed; (b) forbid agents from ever touching TPM tooling — rejected: agents are the operator channel when the CEO says so (D-40); the gate is a launch-time question, not a capability removal; (c) a mechanical launch gate in the scripts — rejected: the scripts cannot know who the CEO wants in the seat per session; the decision belongs in the conversation (D-44), and mechanical gates on conversation steps are not buildable without inventing state the repo deliberately does not track.

**Reason:** The CEO ruling 2026-08-14, stated after a session where an agent diagnosed a fix as needing a TPM round-trip and immediately packed the TPM bundle and started the relay — without asking whether that route was even wanted or who would hold the TPM seat. "The TPM is someone else" is a persona assumption, not a contract; the seat is whoever the CEO assigns, which may be the same model already on the job. Launching a TPM or milestone cycle is a resource/process decision with human cost — informing first is a checkpoint (Rule 4), not ceremony.

**Do not suggest:** reverting to auto-launch of TPM/milestone cycles on agent judgment; assuming the TPM seat is always a separate web-chat model; skipping the ask because "the CEO already knows"; adding a script flag to skip the inform step; treating this entry as superseded by D-39/D-49 (those define the mechanics of the seat, not who holds it per session).

## D-138 — 2026-08-13 — Contract claims use the active milestone delta range, never accumulated history

**Decision:** A plan task may claim a contract pinned to its own file only when that contract id appears in `changed_contract_ids` for the ACTIVE milestone range. `scripts/orchestrate.sh` already computes that authoritative range under D-113: every `DELTA-vN.json` since the last successfully completed spec, including skipped freezes and same-spec resumes. It exports those exact paths to every `validate-plan.py` invocation through newline-delimited `SWBP_ACTIVE_DELTA_FILES`; the validator unions only those files. Standalone validation, where no completion baseline exists, uses only the newest frozen delta. Greenfield remains inert because every surface is new. Unchanged cross-file contracts remain claimable as directly required interfaces; only unchanged self-owned ride-alongs are rejected.

**Alternatives considered:** (a) Keep unioning every retained `DELTA-vN.json` — rejected because a contract changed once in project history then becomes permanently claimable, making the finding-2 minimality gate largely ceremonial as history grows. (b) Always use only the newest delta — rejected in orchestration because D-113 supports one active milestone spanning multiple freezes since the last success; an intermediate freeze's legitimate claim must survive. (c) Recompute the last-success baseline inside `validate-plan.py` — rejected because D-113 already owns and tests that state transition; a second baseline producer could disagree at crash/resume seams.

**Reason:** The finding-2 gate said a task claims only contracts "this milestone changed," but its producer deliberately over-approximated by scanning all historical deltas. That allowed an EM fallback plan to pull old self-owned routes/schemas/errors/UI back into acceptance even though B3 synthesis correctly assigns only active changed ids. Reusing D-113's active range makes the validator and synthesis mean the same thing without sacrificing skipped-freeze recovery.

**Do not suggest:** restoring the all-history union as a conservative fallback (it is over-scope, not safety); narrowing orchestration to the latest delta only (breaks skipped-freeze milestones); rejecting unchanged cross-file interface claims (they are the legitimate dependency channel); deriving a second active range inside the validator. Cross-repo: derived projects receive the scripts and selftests through template sync; their project-owned decision ledger receives D-138 during the same alignment batch.

## D-137 — 2026-08-13 — Contract retirement uses explicit family-scoped tombstones; omission still carries

**Decision:** A staged post-v1 `contracts.json` may retire standing contract surface only through a transient top-level `remove` object whose allowed keys are `routes`, `schemas`, `errors`, `ui`, and `entry_points`, with arrays naming exact standing ids/symbols. `scripts/contracts-merge.py` applies those tombstones before emitting the merged full artifact and strips `remove` from the output. Every tombstone must name an existing item in the stated family, appear once, and not also be staged as an update; unknown, cross-family, duplicate, and update+remove directives fail closed with the name. An omitted contract remains byte-identical carried content under D-136. The ordinary old-vs-new DELTA producer already records removed ids and entry points in `changed_contract_ids`, so retirement participates in affected-task reset and verdict scope without a second bookkeeping channel.

**Alternatives considered:** (a) infer deletion from omission — rejected because omission is D-136's safe carry signal and making it destructive restores silent loss; (b) require a full returned id-array minus the retired entry — rejected because it makes the TPM reproduce accumulated surface it did not receive and cannot vouch for; (c) use one global id list — rejected because a family-scoped directive detects wrong-family names and avoids ambiguity; (d) install tombstones in the frozen full schema — rejected because `remove` is merge procedure, not standing product surface, and must disappear before every downstream gate.

**Reason:** D-136 made additions and updates milestone-minimal but intentionally made omission non-destructive. Without a separate explicit retirement operation, obsolete routes, schemas, errors, UI locks, and entry points could only accumulate forever or force a risky full-file replacement. Family-scoped tombstones complete the staged-delta lifecycle while preserving D-136's central invariant: context not returned by the TPM is carried byte-identical, never silently deleted.

**Do not suggest:** treating omission as deletion; accepting an unknown tombstone as an idempotent no-op (a typo would silently retain the obsolete contract); allowing one item to be both changed and removed; retaining `remove` in installed `scripts/.approved/contracts.json`; adding a second DELTA field for removals (the existing old-vs-new producer already emits removed names in `changed_contract_ids`). Cross-repo note: derived projects receive the merger/refreeze/selftests via template sync, while their project-owned TPM role and decision ledger receive this entry in the same alignment batch.

## D-136 — 2026-08-12 — contracts.json refreezes as a staged merge artifact, not a full-file replacement (SHAPE A)

**Decision:** contracts.json changes enter `refreeze.sh` as a STAGED MERGE ARTIFACT, not a full-file replacement. The TPM returns only changed/new entries (each carrying its `file` pin per D-120/D-124) in `scripts/.approved/incoming/contracts.json`; refreeze merges them onto the standing contracts.json and verifies mechanically: every entry the delta does NOT name changed must remain byte-identical (checksum the untouched remainder); any touched-but-unexpected entry fails closed with the id named; new entry ids must appear in the delta's changed set; entry_points derive from the merged file under the existing deterministic rule. The merge is a PRODUCER: the result still faces the full existing freeze gates (`check-spec-delta`, `check-test-surface`, pin-gate, live interface) — never an authority. The PRD gets an additive-only guard: a staged PRD must contain the standing capsule text unchanged; silent removal of historical acceptance criteria is a fail-closed error (supersessions go through ERD-DELTA as today). The remainder contract extends to the scalar accumulators (no_edit_files, externals, test_mapping, smoke_checks): omitted in the artifact means carried byte-identical from standing; a staged explicit empty is the only way to clear them.

**Alternatives considered:** (A) this staged merge. (B) full-return + mechanical guard — the TPM must reproduce the 15 routes / 46 UI entries it never saw; converts silent loss into loud failure but does not unblock authoring; rejected. (C) restore full PRD/contracts shipment — reverses the D-116/D-117/D-120 context minimalism; rejected.

**Reason:** Full-file replacement makes silent loss the default failure mode — an entry dropped or mutated off-screen ships unnoticed — and forcing the TPM to re-emit the whole standing file to avoid that reverses the D-116/D-117/D-120 minimalism by loading content it never saw and cannot vouch for (alternative B's cost, which still does not unblock authoring). The staged delta ships only what the TPM actually changed, and the mechanical merge converts the silent-loss risk into a loud fail-closed error at the exact granularity of the pins: the untouched remainder is checksummed byte-identical, an unexpected touch dies with the id named, a new id must be declared in the delta's changed set. Keeping the merge a producer — the merged file still faces every existing freeze gate — means the delta shape adds a verification, not a new authority, mirroring how `--synthesize-plan` (D-133) produces a plan that still faces the full `validate()` gate.

**Do not suggest:** restoring full-file shipment (silent loss is the failure mode this replaces; the delta ships only what the TPM changed); weakening the byte-identical checksum to change-tolerant (the byte-identical remainder is what makes an off-target mutation loud); skipping the guard on `--diff` (the CEO must see the rejection at review time, not after apply — the D-134 rule); making the merge a gate-owned authority instead of a producer (it produces a merged file that still faces the full freeze gates — mirror `--synthesize-plan`'s producer-not-authority framing, D-133).

## D-135 — 2026-08-12 — The contracts slice hard-cuts out-of-inventory pins: no `out_of_scope` index (supersedes D-120's index)

**Decision:** `scripts/contracts-delta.py` omits pinned entries whose owning file is outside this milestone's `contracts.files` inventory ENTIRELY — the one-line `out_of_scope` index D-120 specified (id + shape + pin) is removed. The slice is the in-scope contract body only: in-inventory pinned entries in full, every unpinned entry in full (the conservative always-ship-unpinned carry is unchanged), out-of-inventory pinned entries dropped, and entry_points kept only when their derived module is in the inventory. `.opencode/prompts/em.md` is corrected to match: an out-of-inventory interface still exists and is planned from the ERD-delta's integration instructions, never from an invented shape or from its absence in the slice. Enforced by `selftest_gates.py::test_contracts_delta_slices_out_of_scope_pins` (asserts `out_of_scope` absent and out-of-inventory ids/entry_points dropped) and `selftest_b4a.py`.

**Alternatives considered:** (a) Keep the index (D-120's original position) — rejected: the ERD-DELTA already carries the integration instruction authoritatively (D-107), so the index is redundant standing load, and an EM that plans integration from a standing shape rather than the current delta's instruction is the invented-shape hazard D-120 itself warned about. (b) Leave the code as-is and only re-word the docs to still say "index" — rejected: the selftests pin the hard cut; the docs were the drift, not the code.

**Reason:** Ledger reconciliation (2026-08-12): the index was cut in the code and pinned by selftests (the "review-cut") but never recorded as a decision, leaving D-120's entry and its *Do not suggest* clause describing behavior the shipped generator no longer has (the exact code-shipped-without-its-ledger-entry drift the 2026-08-07 correction-log rule forbids). The cut is sound: the integration knowledge D-120 wanted to preserve — an interface a milestone file calls but does not own — is authored explicitly in the ERD-DELTA's instructions, already authoritative to the EM; the one-line index duplicated that while shipping accumulated cross-milestone interface names into every slice, the full-load creep D-120 set out to remove.

**Do not suggest:** Restoring the `out_of_scope` index (the ERD-delta owns out-of-inventory integration context; the index is duplicated standing load); reading D-120's "Do not suggest: dropping the `out_of_scope` index" as still binding (that clause is superseded here); hard-cutting UNPINNED entries too (the always-ship-unpinned carry is the D-120 safety property that keeps the slice degrading to more context, never less, and is retained). Cross-repo: testchat's ledger still carries the un-superseded D-120 and lacks D-133/D-134/D-135 — a ledger-alignment back-port is owed there and is NOT done by this entry.

## D-134 — 2026-08-11 — Freeze-time owning-file pin gate (item 1): every added or modified test function must pin its owner file before the delta can freeze

**Decision:** `refreeze.sh` runs a new mechanical preflight (item 1 of the 2026-08-11 control-plane audit, closing the AC-161 hole): every test function this delta ADDS or MODIFIES — the function-granular changed term of `refreeze_delta.py` (finding-1) — must carry an explicit owning-file pin in `contracts.test_mapping` or the ERD-DELTA `## Test-to-file mapping` section, AT FREEZE TIME. The gate (`refreeze_delta.py pin-gate --old-root . --new-root <staging> [--test-mapping …] [--erd-delta …] <changed test files…>`) diffs the current tree against the staged files with the exact `function_changes` machinery the DELTA producer uses — the gated term and the recorded delta can never disagree — and dies with the unpinned families listed. Pins match at FAMILY granularity (parametrization stripped both sides), so a bare family is satisfied by a `name[chromium]` pin and vice versa. Runs in `--diff` mode too, so the CEO never reviews a delta the pipeline will reject. Grandfathered by design (S6/D-128 lesson): infra-level changes (fixtures, helpers, imports) and carried tests are NOT gated — requiring a pin for every test in a 50-test file whose fixture changed would halt every freeze on old content.

**Alternatives considered:** (a) post-apply gate in the DELTA producer's `main()` — rejected: a failure after apply leaves the tree mutated and a stale DELTA file for D-75 to read; (b) gating the whole-file fallback too — rejected: the infra fallback is a conservative over-scope (an over-run, never an under-run), and the S6 incident proved a hard halt on untouched content freezes the pipeline; (c) requiring the pin owner to be a `contracts.files` member — rejected: D-78/D-107 already validate mapping→inventory and test_mapping→frozen-node-ids; the gate covers pin EXISTENCE, not those already-proved properties.

**Reason:** testchat v99's AC-161 oracle was a genuinely new test riding no pin — the file-granular milestone slice emptied its task and the default verdict could pass without running it. B3 (D-133) refuses unpinned tests on the mechanical path, but the EM fallback still heuristically places unpinned tests; the audit item closes the hole at the SOURCE: a delta that adds or modifies a test without pinning it cannot freeze at all. Reusing `function_changes` means the gate is exactly as granular as the delta — nothing re-implements the diff.

**Do not suggest:** extending the gate to infra-fallback whole-file scopes or carried tests (grandfathered by design — see the S6/D-128 correction-log entry for why a hard halt on old content is a pipeline freeze); weakening the gate to warn-only (the audit item is a halt: an unpinned test is a placement gap the EM cannot be trusted to infer); bypassing the gate on `--diff` (the CEO must see the rejection at review time, not after apply).

## D-133 — 2026-08-11 — Mechanical plan synthesis (B3): the TPM's complete ERD-DELTA transcribes into the plan with no EM call

**Decision:** `validate-plan.py --synthesize-plan DELTA.json [DELTA.json ...]` produces the full plan mechanically when — and only when — the TPM's ERD-DELTA carries a complete decomposition: a verbatim coder brief for EVERY file in `contracts.files` (`## Coder briefs (verbatim)` with `### T<n> — <file> (<label>)` blocks), a DAG statement (a `` `A` depends on `B` `` line and/or a `Task order:` chain), and an ownership pin for every milestone node-id (frozen `test_mapping` ∪ the delta's `## Test-to-file mapping` section). One deterministic task per file: brief verbatim, `contracts` = changed ids pinned to that file (D-120 pins / entry-point self-pins), `tests` = the milestone slice's pinned node-ids, `depends_on` = the DAG prose resolved to task ids. The output still faces the FULL `validate()` gate — the command is a producer, never an authority. On any missing piece it refuses (exit 1, named reasons) and `ensure_plan` falls back to the EM full emission with the reasons as context — **the EM is exception-only in the mechanical lane**. The synthesis attempt consumes no plan-revision budget and fires once per run; a synthesized plan rejected by the gate then feeds the EM's revision loop as `plan-being-revised`, giving the EM a concrete draft to fix instead of a blank slate.

**Alternatives considered:** (a) always-EM emission — rejected: the EM's only authority is judgment the transcription lacks; for a complete TPM briefs package its emission is pure transcription cost (and testchat v99's AC-161 oracle showed a NEW test pinned only in the delta's mapping section silently dropped from the file-granular slice, leaving the task's tests empty — synthesis transcribes the section, closing the D-124 hole); (b) synthesis writing `tasks/plan.json` itself — rejected: the shell owns all writes (D-53); the command prints JSON to stdout; (c) a bounded always-try loop — rejected: the producer is deterministic, a retry after its own gate rejection is pointless, one attempt per run.

**Reason:** Full EM emission dominated plan cost (45–90 min of the review batch) while the TPM-authored ERD-DELTA already contains the decomposition when complete. The milestone's own artifacts (testchat v99: briefs T1–T4, DAG line, mapping section) demonstrate the materials the transcription needs. Fail-closed-to-EM keeps the EM's judgment wherever the TPM data has a gap; the full gate keeps authority regardless of who authored the plan.

**Do not suggest:** having the EM "review" every synthesized plan (its judgment is only for the gaps; a review pass reintroduces the cost with no new authority); emitting `regression` or status keys from synthesis (D-57/D-26 — the shell computes the bucket); trusting synthesis's refusal messages without re-reading the frozen artifacts (they describe the TPM's data, which is the single source of truth); relaxing the brief-per-file precondition so synthesis can run with a partial package (the unbriefed file would fall to a coder with no instructions — that is exactly the EM's judgment seat).

## D-132 — 2026-08-10 — Route pipeline-vs-direct by size and determinism, never the bug/feature label

**Decision:** Every behavior change is routed by size and determinism, not by whether it is called a bug fix or a feature:

- **Direct (ad hoc — no refreeze/orchestrate):** a defined defect with a known root cause whose fix is small and deterministic — a handful of files, no new behavioral scope, no structural test changes; regression tests pin the corrected behavior. Lands as a normal commit on main.
- **Pipeline (milestone):** any change with behavioral scope (new or changed observable behavior needing AC authoring), multi-layer/cross-file work, structural test changes (new `tests/` files, frozen-mapping churn), or work too large to hold in one read — regardless of the bug/feature label.
- **Universal, both paths:** tests are written before the code (red before green, INV-1), and the frozen suite (or the delta's mapped oracle, D-112) is green before "done" — on the sandbox AND the host (the M29 class). A direct fix is the same bar scaled down, never a lower tier.
- **Escapes and reconciliation:** `--no-verify` still requires CEO authorization, and the INV-1 bookkeeping lands with the fix (frozen-manifest pin, as testchat's `f569528`) or a ratify milestone (D-63) catches the spec up — the oracle is never left stale.

**Alternatives considered:** (a) a sizing formula (N tasks / N files / N tests) — rejected at D-83: project-dependent and gameable; the judgment stays with the routing seat; (b) bug fixes always direct, features always pipeline — rejected: the label is packaging, not size — testchat v99 was a bug fix (quarantine visibility, hydration) that needed the pipeline and sailed green, while the model-management bundle was also a bug fix that died in it for spec-authoring defects a direct read would have caught (three freezes, then shipped direct as `7bfc622`); (c) everything through the pipeline — rejected: the ceremony (EM decomposition, task DAG, VM sandbox, coder calls) exists to keep frontier-tier spec work off the code; for a small deterministic fix it is dead weight.
**Reason:** The 2026-08-09 ruling recorded in this file's session notes (`tasks/CURRENT.md`: "the VM + EM/coder + sandbox are for milestone feature runs ONLY, not ad-hoc bug fixes") routed on the wrong axis; this decision supersedes it. The pipeline's value, in order: tests-before-code (INV-1), ACs tied to observable outcomes (spec lint), and only then the ceremony. Routing by size/determinism keeps the invariant guarantees on every path while dropping only the ceremony that adds nothing for small deterministic work — and it avoids two quality tiers, where the low tier is where regressions breed.
**Do not suggest:** routing by the bug/feature label; a mechanical threshold (gameable, D-83); marking a direct fix done on self-judgment — the mapped oracle or the full suite is still the only success verdict; deferring a direct fix's INV-1 bookkeeping "to the next refreeze" (the pin lands with the fix).

## D-131 — 2026-08-08 — Gate-owned resolution of duplicate node-ids: the DAG votes, the EM does not

> Ledger entry restored 2026-08-10: the code shipped 2026-08-08 but the
> entry was never written — the blueprint's `d2e869ac` force-push lost it
> there and the testchat ledger ended at D-129; restored now in both
> ledgers (code and ledger travel together).

**Decision:** A node-id mapped to more than one task is resolved gate-owned by `validate-plan.py` instead of halting — but only after the pinned relocation and the D-64 browser rule have settled every authority-driven placement, and after AUTO_PLACED is reset, so the resolution observes the final plan and its notes survive to the report. The rule: the node's acceptance point is the mapped task that runs LAST in topological order — its dependency closure contains every earlier mapped task, so it is the one mapped task after which the node is provably green. Pinned re-adds are exempt by construction (test_mapping relocation already moved pinned node-ids to their declared owner, and the D-64 sweep skips pinned ids), so anything still over-mapped is UNPINNED. A duplicate surviving the block is a genuine error and halts as before.
**Alternatives considered:** (a) keep the halt — rejected: an over-mapped node is EM mis-placement with a provably correct answer; halting burned escalation cycles on what the DAG can compute (D-05); (b) first-claimant wins — rejected: an early task's projection can pass while a later claimant's file ownership was the real one; last-in-DAG is the only placement after which green is provable.
**Reason:** The EM tier repeatedly fails to honor prose placement rules for backend tests (testchat v88: the storage-quarantine node was placed on BOTH the storage task and the api/threads task twice in a row despite the ERD stating one owner). Same philosophy as D-64: a deterministic placement rule is gate-owned, not EM-owned. The DAG vote can never reject a test the freeze considers well-mapped, because it matches the freeze's own "any task downstream of the node's owner" acceptance view. Selftests pin the resolution and its boundaries (`scripts/selftest/selftest_gates.py`).
**Do not suggest:** trusting an EM prose re-placement of a duplicate (the failure class this resolution removes); resolving before pinned relocation and the D-64 sweep (it must observe the final plan); treating a duplicate that survives the block as resolvable (genuine error).

## D-130 — 2026-08-08 — The milestone node-id scope is the frozen test_mapping intersection, produced once by validate-plan.py

> Mirror of the blueprint entry (same decision, both ledgers; back-ported
> 2026-08-10 after the ledger had drifted).

**Decision:** One producer (`milestone_scope_ids()` in `scripts/validate-plan.py`, exposed as `--milestone-scope`) computes the node-id set a delta run is about: the raw `changed_tests` intersected — on the **family** (module prefix + bare test name, parametrization-suffix-stripped) with the frozen `test_mapping` keys, plus the D-124 completeness repair (pinned ids whose owner FILE the delta staged ride even when refreeze_delta dropped them from changed_tests). Both scope consumers call it: `cmd_subtree_scope` (map_nodeids + `_hit_task_ids` invalidation) and `cmd_affected` (the task-state reset scope), and orchestrate's full-emission `NODEIDS_SCOPE` now shells out to `--milestone-scope` instead of inlining its own union. When the mapping is empty (a pre-D-124 freeze), the slice is inert — raw rides, the trim must not bite before pins exist.

**Alternatives considered:** (a) intersect in orchestrate's inline union only — rejected: parity between the subtree scope and the full-emission prompt was exactly the defect (orchestrate-testchat v87: refreeze_delta's file-granular changed_tests carried 58 — the 6 pinned M35 ids plus 52 relabeled leftovers of the same test file — and both surfaces shipped all 58 to the EM and the invalidation set, re-planning two tasks on churn); one producer in the Python gate is the structural fix, and it is directly unit-testable where the heredoc was not. (b) Intersect changed_tests with the exact mapping value — rejected: node-id shape flicks between freezes (D-124: `name[chromium]` vs AST's bare `name`); an exact-string intersect would filter the milestone down to nothing on a relabel and the D-124 flip would reappear at this site.
**Reason:** The audit (2026-08-08) isolated the class: file-granular changed_tests conflate "this file changed" with "this test belongs to this milestone"; only the TPM's frozen pins are behavioral-ownership truth. Family-matching survives both presentation shapes. `test_mapping`-containing freezes — the only ones where the trim has teeth — are the modern lane; inert fallback defeats the trim before D-124-class pins arrive (blueprint's own fixture freezes carry no mapping).
**Do not suggest:** Slicing refreeze_delta's changed_tests at production time (the producer intentionally keeps full counts for the DELTA file's bookkeeping; D-116's file-scoping already fixed the relabel-retirement term); re-adding a divergent union inside orchestrate.sh for "it's clearer"; dropping the family-match for exact ids once "the churn settles" (the flip is a presentation of the same suite, not a past incident — D-124); making the slice a no-op when a sibling runs have a mapped file (per-delta slicing is what makes the union add up).

## D-129 — 2026-08-08 — mypy is an acceptance gate in the sandbox, not a CI-only survivor

**Decision:** `run_tests()` runs `mypy --explicit-package-bases --cache-dir=/tmp/mypy-cache src/` inside the sandbox before any pytest invocation; a type error fails the acceptance (rc=1, FAILING=mypy:src) and the pytest run is skipped; CI keeps its own mypy step.
**Alternatives considered:** (a) keep mypy CI-only — the M29 `psutil` class proved a gate living only in CI does not exist until a child has a remote (testchat shipped 40 spec versions with a dark type gate, red on first push); (b) host-side mypy — host stack is not the pinned sandbox stack (D-50) and the acceptance is the sandbox (D-53).
**Reason:** mypy 2.1.0 + types-psutil already in requirements.txt/Containerfile — no rebuild, no dependency add. Live probe: `mypy --explicit-package-bases src/` green (11 files, no issues); requires `--cache-dir=/tmp/mypy-cache` because the repo mounts read-only and mypy insists on writing `.mypy_cache`. Fail-closed: a sandbox stack missing mypy hard-halts, never skips. Selftest stub distinguishes the mypy invocation from pytest (SANDBOX_MYPY_RC); 306 selftests green in both repos.
**Do not suggest:** moving the type gate back to CI-only, or running mypy outside the D-30 sandbox (stack-divergence is the defect class being closed).

---

## D-128 — 2026-08-08 — Reverse-direction spec lint (S6): whole-world-mock rejection and carried-tests-vs-new-ACs citation check

> Mirror of the blueprint entry (same decision, both ledgers; the gate is
> template-owned, synced via the template manifest).
> **Amended 2026-08-08 (same day):** check 1 (whole-world mock) is scoped to
> the tests THIS DELTA TOUCHES, not the whole merged suite — this repo's own
> frozen suite carries 9 legacy bare-Mock whole-world patterns
> (test_models_api.py:140/166/319, test_models_service.py:159/181/190/202/
> 214/357); a whole-suite halt would brick every refreeze on content no
> milestone is about. Now: staged bare mock rejected, carried legacy mock
> grandfathered, standalone invocation still audits the whole directory.

**Decision:** A refreeze preflight (`scripts/check-test-direction.py`, "S6") rejects (1) a suite mock — carried or staged — that answers every URL (a URL-verb fake whose callable ignores its URL argument, or a bare `Mock()`), and (2) a carried-forward test that cites an AC id this delta adds. Both halves run on the merged preview suite (current frozen + incoming overlay) before the freeze applies.
**Reason (the v58 incident):** The forward lints compare STAGED tests against LIVE ACs; v58 passed them and still shipped the reverse contradiction — a carried test that monkeypatched `httpx.get` to return 200 for every URL made the "other" script model read as loaded, so the new AC-104 spawn-refusal never ran and the test asserting `Popen` was called could not fail. A whole-world mock encodes "the whole world is ready" and silently couples unrelated subsystems; the citation check is freeze-lane attribution (a test whose assumptions predate an AC this delta adds must ride the delta or the 'new' claim is false).
**Do not suggest:** Demoting either half to advisory without a measured false-positive (D-115); moving the scan off the merged preview into CI (it would race the S-LINE staged/preview erased-state class); tightening the mock analysis beyond "reads its URL parameter" (speculative pre-hardening, D-32).

## D-127 — 2026-08-08 — The sandbox has never run as root and the constraint-2 verifier now proves it mechanically

> Mirror of the blueprint entry (same decision, both ledgers; sandbox and its
> verifier are template-owned).

**Decision:** The sandbox runs pytest/smoke runs as the image's non-root `agent` user (UID 1000 — `USER agent` in the Containerfile, `--userns=keep-id --cap-drop=ALL --security-opt no-new-privileges`), and `scripts/selftest/verify-sandbox-in-vm.sh` gains check [6]: the sandbox process uid must be non-root.

**Reason (the M29 incident, corrected):** The sandbox has been unprivileged since the template bootstrap; the M29 failures were a macOS-vs-Linux psutil semantics difference (module-level `net_connections()` is a macOS root-only call; the Linux container never needed root). The P1 backlog item's premise ("the container runs as root") was wrong — and the missing piece was never the user, but the PROOF. The verifier checked mounts, rw lanes, and network but never the process user, so a silent drift to a root-running image could never fail loud. Check [6] makes the property mechanical.

**Do not suggest:** running the sandbox as root for any convenience; dropping the non-root assertion from the verifier; asserting the property from the host instead of inside the container.

## D-126 — 2026-08-07 — The metrics layer: a per-milestone aggregate over the data the pipeline already writes; metrics.tsv is the D-115 admission input

**Decision:** `scripts/metrics-report.py` aggregates ONLY post-teardown-durable sources — `.measurement/counters` (per-run exit rows with `rc=`, `spec=`, `elapsed=`), `.measurement/timings-<TS>.tsv` copies, `.em-archive/*/meta.txt` (spec-tagged), `.pipeline-flakes.json` (committed, D-111) — into one TSV row per milestone in `.measurement/metrics.tsv` (columns: milestone, date, feature, gate_hours, selftest_count, selftest_s, em_calls, em_waste, flakes, success_runs, retry_runs). The row is idempotent per milestone+feature (D-111 habit), scoped to one spec version across all sources, and `--evidence` prints the same numbers without writing — the measured-evidence block a D-115 retirement entry must cite. On success, the terminal rc=0 counter and timings copy are persisted before `.pipeline-state` teardown; the EXIT trap then skips that already-recorded event. After the `[success]` commit, the reporter reads the durable sink and records the aggregate automatically (`--feature v$FROZEN_V`; a report can never fail a run). D-108's lesson, applied: `.pipeline-state` is wiped by the success teardown (`rm -rf`), so the aggregate is computed after the wipe from what outlives it — never stored inside the blast radius. It is a report, never a gate: nothing in the completion path reads metrics.tsv.

**Alternatives considered:** (1) A new data-capture layer inside orchestrate.sh — rejected: the substrate already exists and feature-summary.py already reads it; the complexity ratchet (review 2026-08-07) forbids a new writer where readers suffice. (2) Building the aggregation into feature-summary.py — rejected: that digest is human-facing prose scoped "since last refreeze"; metrics needs machine rows keyed per milestone, one concern per script. (3) Making D-115's admission precondition a blocking gate — rejected: retirement stays a human decision on measured evidence, not an automated one.

**Reason:** The completion gate (D-112 verdict) answers "can this milestone ship?"; the metrics layer answers "how much did shipping it cost?" — per-feature gate time, EM waste, flakes, retries. D-115's admission rule ("retire on measured cost, not complexity aesthetics", D-117) stalled for lack of per-feature numbers: the substrate existed but nothing aggregated it per milestone, so retirement candidates (D-83/D-56-NOTE/D-89 were the only ones retired, on hand-measured data) had no standing evidence. With metrics.tsv, a retirement entry can cite gate-time share across ≥3 milestones, flake history, and behavioral-change evidence instead of prose. Blueprint decision of the CEO 2026-08-07 (primary purpose: shipping-pipeline verdict).

**Do not suggest:** (1) wiring metrics.tsv into the completion path or any gate — it stays a report. (2) adding new writers to orchestrate.sh/refreeze.sh to produce "better" metrics — reuse the existing substrate. (3) inventing fields not derivable from the four listed sources. (4) folding metrics into feature-summary.py or vice versa — separate concerns, separate scripts.

## D-122 — 2026-08-06 — A freeze must be visible to the DELTA-vN bookkeeping: claimed updates ship their bytes, invisible-only contract changes are rejected

**Decision:** `scripts/check-spec-delta.py` (the D-107 delta gate, already a refreeze preflight) gains a completeness layer with two fail-closed checks. (1) If the staged ERD-DELTA.md marks a frozen test as UPDATED, the freeze must actually stage changed bytes for that test's file (byte-diff against the repo; `REMOVED` entries count) — a claim without bytes is rejected. (2) If the staged `contracts.json` changes only bookkeeping-invisible top-level keys (`files`, `test_mapping`, `smoke_checks`, `no_edit_files` — not the `entry_points`/`routes`/`schemas`/`errors`/`ui` families the DELTA-vN walk records, and not `changed_files`/staged test bytes), the freeze is rejected as unscopable. Marker matching is case-sensitive by design: mapping sections carry the `(UPDATED)` marker; historical prose ("was updated at v80") describes a prior freeze, not this one.

**Reason:** The DELTA-vN file is the orchestrator's ONLY scope source — subtree reset, verdict scope, red-check (D-31/D-112). The v82 freeze was exactly the failure class: its ERD-DELTA claimed the AC-153 tests were "(UPDATED: model selected before pressing the shortcut)" while the freeze staged no test bytes, so DELTA-v82 recorded `changed_tests: []` and the milestone's central claim was invisible to every later run; the mirror class (v77) recorded ~50 byte-identical restaged tests and re-ran finished work. A claim the bookkeeping cannot record is a lie-green risk, and an invisible-only contract change (e.g. a freeze touching only `test_mapping`) would produce `changed_contract_ids: []` — the run would reset nothing. Both are pre-flight detectable, and D-122 makes them hard errors instead of the D-86 "scopes nothing" warning. CEO-authorized 2026-08-06 after a brief ("cheap insurance against a class that already happened").

**Do not suggest:** Downgrading either check to a warning (D-86 already proved the warning is ignored); relaxing the byte-diff (claimed updates must be byte-visible, not presence-visible — the v82 claim staged no bytes); case-insensitive marker matching (it would flag historical prose and every freeze would fail); carving out `smoke_checks`-only or `test_mapping`-only freezes as "metadata" (metadata IS the scope — the orchestrator lives or dies on it).

## D-121 — 2026-08-06 — The refreeze lane has no human approval step: installs are gate-verdict-only

**Decision:** `scripts/refreeze.sh` no longer offers ANY human-approval path. D-95's auto default — apply when every mechanical preflight is green, halt on any failure — is now the only apply mode; the `--approve <sha>` (D-42 hash-bound explicit apply) and `--interactive` (opt-in y/N) flags are removed and die on use with a pointer to the auto install. `--diff` remains as a read-only dry-run (prints the diff and DIFF-SHA, applies nothing). The audit line `auto-approved (D-121); DIFF-SHA <sha>` is printed on every install. The CEO ruling verbatim (2026-08-06): "remove ceo approval for refreeze run — the business ceo or human can't add any value there." Landed immediately before the v83 pin-freeze, so the backfill installs under the new policy.

**Reason:** Every material check already ran mechanically before apply (schema structural core, D-107 spec-delta, D-120 pin gate, D-56 externals/captures, INV-4 test surface, D-78 satisfiability, staged-test parse/lint/determinism, D-75 red-before-green, M35 smoke red-check); the diff is machine-authored; and the human verdict on it was a documented rubber-stamp — five straight testchat refreezes v60–v64 on ~62KB re-touched ERDs the CEO could not judge, with the CEO delegating approval to the model as an interim on 2026-07-27. D-121 closes the loop formally: a verdict nobody consumes is not a gate, and an approval nobody can meaningfully give is not a control.

**Alternatives considered:** (a) Keep `--approve`/`--interactive` but never use them (rejected — a dead flag is a lie; the lane must fail loudly if reintroduced, hence die-on-use). (b) Keep `--interactive` for rare eyeball cases (rejected — `--diff` already provides the eyeball without an apply path; the CEO ruled the human adds no value on the diff itself). (c) Move the approval to orchestrate.sh (rejected — the same rubber-stamp critique applies, and the refreeze lane is the single place frozen artifacts change, D-31).

**Do not suggest:** Re-adding a y/N prompt or hash-bound `--approve` to refreeze.sh (die-on-use is the removal's regression guard); treating `--diff` as an approval gate (it is a preview only); moving the human gate into orchestrate.sh (the CEO ruling applies to the diff, wherever it is shown).

## D-120 — 2026-08-06 — The EM's contracts context is the milestone slice: pinned entries for in-scope files, trimmed at plan time

> **Superseded in part by D-135 (2026-08-12):** the one-line `out_of_scope` index described below — and defended in this entry's *Do not suggest* — was removed; out-of-inventory pins are now hard-cut. The pin gate and the always-ship-unpinned carry remain fully in force.


**Decision:** The four plan-emission sites (greenfield, subtree re-plan, decomposition-wrong re-emit, drift re-plan) ship `contracts:${CONTRACTS_DELTA:-$APPROVED/contracts.json}` — a pre-flight-generated slice, never the full accumulated file. `contracts.schema.json` gains an optional `file` property (pattern `^src/.*\.py$`) on routes/schemas/errors items (`additionalProperties:false` retained; `entry_points` stay self-pinning by dotted-module derivation); `check-spec-delta.py` rejects any NEW or CHANGED entry without a pin at freeze time (carried-unchanged entries are exempt — nothing new is added, so nothing can be lost); `scripts/contracts-delta.py` emits pinned entries whose file is in this milestone's `contracts.files` inventory in full, plus every unpinned entry in full, and reduces pinned entries outside the inventory to a one-line `out_of_scope` index (id + shape + pin) so the EM still sees the interface exists and plans its integration from the ERD-delta rather than inventing a shape — entry_points derive to their owning module under the same rule. While NO entry carries a pin, the generator emits the full file byte-identical — the trim activates inertly the moment pins land. The DRIFT/SPEC-DEFECT consult keeps the full file (D-116: it judges the whole decomposition). The 40-entry backfill itself is TPM-seat, specified in `project-trail/2026-08-06-contracts-file-pin-proposal.md` (BACKLOG P1).

**Reason:** CEO audit directive 2026-08-06: no irrelevant full-load work — "just like we cut back on coders work from reproducing full file to just producing diff code." contracts.json is the standing accumulator (74 entries at v82, 554 lines); the EM needs bodies only for the files this milestone touches. The pin makes the trim safe and mechanical: a freeze-time gate that demands a pin for anything new or changed means the slice can never silently drop a body the EM plans against, and the conservative always-ship-unpinned rule means the slice degrades to the full file, never to less, when the TPM misses a pin. The index exists because integration context crosses file boundaries: a milestone file may call an endpoint owned by a file outside the inventory, and a hard cut would let the EM brief blind against an interface it can no longer see — the one-line entry preserves existence and shape knowledge at a fraction of the body cost. The schema + gate are conductor-lane and land in the same freeze session that consumes them; the backfill is TPM-seat because only the spec author knows which file owns each entry.

**Alternatives considered:** (a) Trim by `test_mapping`/files-mapping heuristics without pins (rejected — the gate needs frozen data it can hold you to; a derived guess can silently drop a body mid-run). (b) Trim `entry_points` by membership without derivation (rejected — the file inventory is paths; dotted modules must map or they never match). (c) Author the 40 pins myself (rejected — TPM-seat, and recorded as such).

**Do not suggest:** Removing the pin gate to speed freezes (a slice without the gate is a silent-drop hazard); dropping the `out_of_scope` index and hard-cutting out-of-inventory entries (integration context crosses file boundaries — the EM briefs blind against interfaces it can no longer see); trimming `entry_points` against a hand-maintained module list (derivation is deterministic); shipping the full contracts to the DRIFT/SPEC-DEFECT consult (it judges the whole decomposition, D-116); authoring the backfill pins in the conductor lane.

## D-119 — 2026-08-06 — Re-plan calls get the scoped node-id list, not the full test-nodeids file

**Decision:** The decomposition-wrong re-emit and the spec-drift re-plan no longer ship the full 198-id `test-nodeids` file to the EM. Both instructions now print a flat, delta-scoped list — `$(plan_mapped_ids)`, the deduplicated union of node-ids the current plan maps, in task order (the same extraction as the D-112 verdict union) — and the context drops the `test-nodeids:` block. The EM keeps its safe-omit rule, and the validator names any node-id it must still map. The greenfield plan emission (no prior plan exists to anchor a scope on) keeps the full file.

**Reason:** Carried node-ids never appear in the plan — the shell routes carried coverage itself — so the plan's own mapped union IS the delta scope. A decomp re-plan must remap exactly that set (carried mappings are preserved byte-identical per the instruction); shipping all 198 ids forces the EM to re-derive the delta boundary from a file the shell already knows. This closes the last full-load EM site after D-116: standing ERD, contracts-coder, consult, and now node-ids are all scoped; only the greenfield plan emission and the DRIFT/SPEC-DEFECT full-context branch intentionally carry full files.

**Alternatives considered:** (a) Reuse `$STATE_DIR/subtree-scope.json`'s `map_nodeids` (the delta re-plan's list) — rejected: it is computed by `compute_active_delta_scope` only AFTER these calls fire, and `plan_mapped_ids` is derivable from data already on disk. (b) Ship a delta-scoped node-ids file computed from `contracts.test_mapping` — rejected: v82 has no `test_mapping`, and the plan's union is available at every re-plan site regardless of spec version.

**Do not suggest:** Removing the full file from the greenfield emission (no plan yet — the EM needs the full list or the validator's must-map loop runs it blind); adding the file back to re-plan calls; renaming `plan_mapped_ids` or folding it into the verdict block (drive-verdict.sh extracts that block by marker; the helper must stay standalone).

## D-118 — 2026-08-06 — Escalation bundles carry the milestone slice: the standing summary + ERD-DELTA the TPM must revise against

**Decision:** `package_escalation` now appends the milestone slice to every TPM-bound bundle: the generated standing summary (the same `standing-summary.md` the EM receives, D-116) and the frozen `ERD-DELTA.md` (D-107), labeled with the spec version, in a dedicated section between the EM diagnosis and the referenced-contract/test-source section. A consolidation freeze with no delta emits a one-line note that the standing ERD is the current reference. The summary-generation fallback of the D-116 pre-flight is inherited via `STANDING_SUMMARY`.

**Reason:** The 2026-08-06 context audit found the inverse of full-load: `contract_or_test_wrong` and caps-exhausted bundles handed the TPM the task entry, the referenced contract entries, and the failing test sources — but not the delta those artifacts must be revised against. The TPM has no repo access; the bundle is its only spec window, and a verdict that says "the frozen spec is wrong" without the current-change slice forces the TPM to reconstruct the milestone from memory. The delta is the authoritative current-change slice (D-107) and the standing rules are the same minimal summary the EM consumes — adding both is a pure relevance win with no schema change.

**Alternatives considered:** (a) Point the TPM at the repo in agent mode (already available via `tpm-agent.sh`, D-39 — but the primary lane is the air-gapped web chat, D-38). (b) Bundle the full standing ERD instead of the summary (rejected — exactly the accumulative crud D-116/D-117 exist to avoid). (c) Attach the delta only when the verdict is `contract_or_test_wrong` (rejected — a caps-exhausted bundle also lands in TPM hands and may need the same slice; unconditional is simpler and the cost is one file).

**Do not suggest:** Dropping the milestone slice from bundles to save tokens (it is the single most load-bearing file the TPM receives); shipping the full standing ERD in bundles (the summary + delta is the correct pair); reverting to `APPROVED`-free extraction harnesses in the selftests (the bundle code reads `APPROVED` like every other orchestrator function).

## D-117 — 2026-08-06 — The TPM bundle ships the milestone slice: generated standing summary + ERD-DELTA, not the accumulated standing ERD

**Decision:** `tpm-pack.sh` no longer packs the full standing `ERD.md` when a delta exists. When `ERD-DELTA.md` is present, the bundle carries the TPM role doc, the contracts schema, the PRD (standing — the product definition is reference, not crud), the same generated standing summary the EM receives (D-116), `ERD-DELTA.md` (the authoritative milestone slice, D-107), and `contracts.json`. Without a delta (initial freeze, pure consolidation), the full standing ERD ships as before. Summary-generation failure falls back to the full standing ERD with a stderr warning — the bundle is a verbatim relay (D-49), so the warning stays out of it.

**Reason:** CEO audit directive 2026-08-06: "the TPM work — PRD and ERD — should be relevant to the milestone feature, not accumulative crud." The standing ERD is the accumulator (264 lines at v71 → 217 after the v78 consolidation → 252 now): every milestone's as-built detail lands in it, and every TPM session previously received all of it on top of the delta it actually revises against. The TPM's milestone work consumes exactly the delta plus the standing rules the delta supersedes or builds on — the same minimal standing slice the EM consumes — so the pack now ships that slice. PRD stays full: it is the product definition (stable, rarely touched) rather than accumulated implementation history; a PRD-DELTA mechanism remains a possible future refinement if product prose ever accumulates the way architecture prose did.

**Alternatives considered:** (a) Ship full ERD + delta, unchanged (the status quo — rejected: exactly the accumulative crud the CEO named). (b) A new PRD-DELTA artifact analogous to ERD-DELTA (rejected for now: the PRD has not demonstrated the growth problem; standing product reference is legitimate context). (c) Let the TPM fetch the ERD itself in agent mode (D-39 already allows this when available — the web-chat air gap, D-38, remains the primary lane and still needs the packed bundle).

**Do not suggest:** Re-adding the full standing ERD to the TPM bundle when a delta exists; moving the fallback warning into the bundle (it is a verbatim relay); shipping `src/` or `tests/` to the TPM (INV-1 oracle independence); hand-maintaining a summary file instead of generating it (the generator is deterministic and gate-pinned, D-116).

## D-116 — 2026-08-06 — Context minimalism: the EM's standing ERD is a generated summary, the coder's context drops the contracts, and task consults are scoped to the task

**Decision:** Three fixes to the EM/coder call contexts, per CEO audit directive 2026-08-06 ("fix all three") on where the pipeline ships irrelevant full-load context. (1) The standing `ERD.md` no longer ships to the EM in any call. `scripts/standing-summary.py` generates a standing context at pre-flight: the standing rules (model-selector invariant, file inventory, oracle mapping, smoke checks, risk notes) verbatim, with the three accumulated "As-built architecture" sections collapsed to a per-file map. Every EM call site (plan emission, subtree re-plan, drift re-plan, consult) ships `standing:<generated>` plus the authoritative `ERD-delta` (D-107) instead of the full standing ERD; generation failure falls back loudly to the full ERD, never a silent context shrink. (2) `run_coder`'s context is brief + the existing file only — the frozen `contracts.json` is no longer pasted per call; the coder brief is self-contained by rule (Rule 8: exact path, signatures, inputs/outputs, acceptance). (3) `consult_em` is scoped: a task consult ships that task's plan entry (extracted to `.pipeline-state/consult-task-<id>.json`), the standing summary, the delta, and the evidence-grepped failing test file(s) — not the full plan, standing ERD, or contracts. DRIFT and SPEC-DEFECT consults keep the full context: they judge the whole decomposition.

**Reason:** The full ERD shipped in every EM call (252 lines), the full contracts in every coder call (554 lines), and a full-spec consult per task failure — all of it context the called tier does not act on, growing the prompt with every milestone while the actionable slice stays small. The EM plans deltas against `ERD-DELTA.md`; the standing doc's only standing value is its rules and a file map of ownership. The coder's acceptance is the brief, and the brief is authored to be complete; the contracts added tokens, not signal (and had already been the source of a past contamination class — brief/contract disagreement). Consults ask a single question about a single task; shipping the whole decomposition invites the model to re-litigate what the plan already decided. The D-116 doctrine: a model call receives exactly the load its output artifact consumes; everything else is token cost with hallucination surface. Escalation bundles are untouched: the TPM has no repo access, so self-contained bundles stay the requirement there.

**Alternatives considered:** (a) Let the EM lazily fetch what it needs (rejected — the EM has no tools and never will, D-53; context is the orchestrator's job). (b) Summary-only standing doc maintained by hand (rejected — maintenance drifts and humans forget; the generator is deterministic and gate-pinned). (c) Ship contracts to the coder only when the brief references a contract id (rejected — a grep for `contract` is a weak proxy, and the brief already carries everything verbatim).

**Do not suggest:** Re-adding the full standing ERD or contracts to any EM/coder call; letting the model fetch context; trimming the delta or the failing-test evidence from consults (they are the actionable slice); cutting escalation bundle self-containment (TPM has no repo access); growing the standing summary back into the accumulated architecture prose.

## D-112 — 2026-08-06 — Feature verdict is the delta's dependent set; the full suite is an on-demand check

**Decision:** Milestone completion is no longer the full frozen suite. After all tasks are done, the verdict run re-executes exactly the union of every test node-id the plan mapped — the delta's dependent set — and green there is `[success]`. A carried-forward test is not part of milestone completion, and a red carried node can never halt a milestone or route a TPM bundle. The full frozen suite survives as an explicit on-demand/periodic regression check: `scripts/orchestrate.sh --full-suite` runs the whole suite at the verdict point, where the D-77 flake triage and the DRIFT halt apply unchanged (a genuine carried regression still reproduces in isolation and routes EM→TPM — the owning behavior is outside the delta, so the fix belongs to the spec/TPM lane, never a coder retry). In mapped scope a red verdict is drift by definition — every node was accepted per-task, so a failure is an inter-task coupling break — and keeps the existing EM consult → plan revision → TPM bundle ladder. A plan mapping zero tests (smoke-only tasks) skips the verdict run entirely: per-task acceptance is the verdict, never a vacuous full-suite run. Supersedes D-28's "feature completion = FULL frozen suite green" clause; per-task projections (D-28/D-57), the exactly-once mapping invariant, and the spec-drift routing are unchanged.

**Reason:** The full-suite verdict has cost ~45–60 min per milestone and grown with the suite, while its only real signal is coupling the static dependency analysis cannot see — and the CEO doctrine stated at M28 close-out (2026-07-19) and reaffirmed 2026-08-06: "if a feature does not touch a behavior, we do not have to test; only dependent-based testing." D-77 landed the flake-triage half of the M28 candidate; the other half — "skip the drift path if the failing test's file is not in contracts.files" — never landed, and the verdict rule itself never changed. This decision lands both: unrelated failures neither run nor halt, and the coupling backstop the full suite provided becomes an explicit, on-demand check whose failures route to the correct lane instead of blocking unrelated work. The mapped union is cheap: per-task acceptance already ran these node-ids, so the verdict is a re-verification of the projections against the finished tree.

**Alternatives considered:** (a) Keep the full suite but never halt on unmapped failures (the M28 candidate verbatim) — still burns the full wall-clock every milestone for evidence nothing consumes. (b) Report-only full suite with no halt — silently converts the coupling backstop into a suggestion. (c) Drop the full suite entirely — removes the only mechanical check that crosses the analysis's blind spots (shared-file coupling, DOM-level breaks invisible to module-import analysis).

**Do not suggest:** Re-adding the full suite to milestone completion; treating a red --full-suite check as a milestone failure when tasks are green (it routes to the TPM lane); marking a task done on self-judgment because the verdict scope shrank (mapped acceptance is still the oracle); running orchestrate.sh on the macOS host (D-55).

## D-125 — 2026-08-04 — The frozen suite is size-governed: parsimony and retirement are spec properties, TPM guidance, not gates

**Decision:** `docs/TESTING.md` gains two standing rules for the frozen suite. (1) **Parsimony:** one test per acceptance criterion is the default; a second test is justified only by exercising a different surface (unit vs API vs UI) or a distinct failure class — when a unit test and an API test would assert the same fact, one is carrying the other. (2) **Retirement:** a frozen test that has not failed for five consecutive milestones, or that no longer maps to a current acceptance criterion or locked surface, is a retirement candidate the TPM flags at the next refreeze; removal happens through the same `refreeze.sh` delta path as any other spec change, never by direct edit. Suite size is a review item at every freeze: a `tests/` diff without a corresponding PRD acceptance-criterion change is a smell. Both rules are advisory TPM guidance, deliberately not mechanical gates: per-node failure history is not tracked, so a mechanical dead-test detector has no input data, and per D-115 a check with no consumer is decoration. The mechanization path is named in TESTING.md (a failure-history ledger — the D-111 flake ledger tracks only accepted flakes, not "never failed") — adopt only if frozen-suite bloat incidents arrive. Separately: retiring D-88 (quote-brittle smoke-check preflight) and trimming `check-test-surface.py`'s selector blocklist were evaluated and **rejected**. Each is incident-purchased; D-88's entry carries an explicit anti-retirement clause ("do not suggest: demoting to advisory once 'we haven't seen a false positive in N freezes'") and its check is ~130 lines scoped to grep-family/literal-quote/new-entry patterns; the selector families map 1:1 to the 2026-07-11 audit findings (bare-tag selectors, role/text locators, raw CSS/XPath, `locator()`/`query_selector`, data-testid literals), with the blocklist backstops covering receivers the main rule cannot see.



> Renumbered from D-117 on 2026-08-07 (ledger alignment): D-117 now designates the TPM-bundle-slice decision back-ported from testchat; this size-governance entry is D-125.



> Ported from the blueprint 2026-08-07 (ledger alignment; same decision, blueprint numbering).

**Reason:** The frozen suite is the only artifact class in the system with no size governance: it can only grow (removal requires a TPM round-trip through refreeze), every entry is collected/parsed/diffed on each run, and testchat's 18-file/4,287-line accretion shows the pattern. The 2026-08-04 review pass found the example suite itself proportionate (234 lines pinning a 37-line PRD, one test per criterion) but the *direction* structurally one-directional; these rules close that direction cheaply at spec time — where test authorship already lives — without adding pipeline machinery. The D-88/selector retirement proposal is recorded here because it was seriously considered and stopped at the D-record's own evidence: per D-115, retirement requires *measured* blast radius vs cost, and "the check is complex" is not evidence of false-positive cost.

**Alternatives considered:** (a) A mechanical dead-test detector (failure-history ledger + freeze-time advisory) — rejected: no data source exists (the flake ledger tracks flakes, not never-failed tests), and per D-115 a new paid check needs blast radius > cost; TESTING.md names this as the escalation path if bloat incidents occur. (b) Retiring D-88 — rejected: its entry's "do not suggest" was written against exactly this proposal, and no track record exists either way (the gate is a week old). (c) Trimming selector regexes — rejected: each regex is a distinct audit finding's accident class; removing one reopens that family. (d) Enforcing suite size with a line-count cap — rejected: length is a smell, not a violation.

**Do not suggest:** Mechanizing retirement before failure history exists; a line/function-count cap on `tests/` (blocks legitimately thorough suites); reviving the D-88 demotion or the selector trim without new false-positive evidence; repurposing the D-111 flake ledger to track "never failed" (that is a different ledger with a different consumer — name the consumer first).

## D-124 — 2026-08-02 — A node-id relabel in a byte-identical suite must not widen the freeze delta

**Decision:** `refreeze.sh`'s delta computation is extracted into `scripts/refreeze_delta.py` (a real producer with a direct unit test), and its "removed" term — `old_nodeids - new_nodeids` — is scoped to node-ids whose source FILE actually changed in this delta (`changed_files` ∪ `removed_files`). A node-id that disappears from the collected set only because collection relabeled it (pytest's parametrized `name[chromium]` when the sandbox collect succeeds vs static AST's bare `name` when it does not) no longer enters `changed_tests` while its file is byte-identical and still present. The "in changed files" term is already file-scoped and is unchanged. Genuine retirements (files in `REMOVED`) and real edits (staged byte-different files) still populate the delta exactly as before.



> Renumbered from D-116 on 2026-08-07 (ledger alignment): D-116 now designates the context-minimalism decision back-ported from testchat; this relabel entry is D-124.



> Ported from the blueprint 2026-08-07 (ledger alignment; same decision, blueprint numbering).

**Reason:** testchat's v77 re-freeze staged a byte-identical suite, but collection flipped 60 node-ids from the parametrized to the bare shape. The old removed term counted all 60 as retirements, so the delta invalidated and re-ran three already-done, green tasks off a phantom scope — the frozen suite, the app, and the requirements were all unchanged; only the labels flickered. The frozen `test-nodeids` file legitimately churns shape between freezes depending on whether the sandbox collect succeeds; that instability must not translate into work. Scoping the removed term to files the delta actually touched neutralizes both flip directions (parametrized→bare and bare→parametrized) without weakening real-removal detection. The computation moved to its own module because the delta runs post-apply, past `--diff` — an inline heredoc could not be unit-tested, and the correction-log meta-rule (adapters need a real producer test) applies.

**Alternatives considered:** (a) Stabilize the frozen node-id set itself so it never flips shape (always AST, or always pytest) — rejected: AST cannot see parametrization (undercounts) and pytest collect is not always available at freeze time (INV-1 tests precede their imports); the set's shape is legitimately environment-dependent, so the delta must tolerate it rather than the set being forced. (b) Compare node-ids with parametrize suffixes stripped — rejected: brittle to any future id-shape change and would also mask genuine parametrization changes in a truly edited file. (c) Leave it inline and test end-to-end only — rejected: the existing `freezable_repo` end-to-end tests cover the apply path but cannot cheaply exercise the collection flip; a direct producer test pins the guard precisely.

**Do not suggest:** Re-widening the removed term to the raw `old - new` set "to be safe" (that is the defect); forcing the frozen node-id set to a single collection method; auto-editing the frozen spec to prune stale entries (the spec is human/TPM-authored — machinery surfaces, never edits it, per D-75's warn-only stance).

## D-115 — 2026-08-02 — Retire non-decisional freeze advisories; admit/retire safeguards on measured blast radius

**Decision:** The `refreeze.sh` freeze-time advisories D-83 (fresh-milestone note), D-56's ZERO-external NOTE, and D-89's per-file ERD prose-mass advisory are retired. `refreeze.sh` no longer prints them; `validate-plan.py` keeps only D-89's plan-gate half (the `MAX_BRIEF_CHARS` overflow hint names the ERD section size when a brief is actually rejected); `ERD-MASS` is no longer a preflight. Retiring an advisory is a doc-level amendment to the originating D-entry (D-83, D-56, D-89, D-107's "concatenates before running D-89" clause) — history stays, intent is updated. All hard gates are untouched: D-78 satisfiability, D-88 smoke quotes, D-87 static-asset, D-107 ERD-delta validation, INV-4 surface, staged-test parse+lint+determinism, D-75 red-before-green, the plan gate, and every coder/EM lane.



> Ported from the blueprint 2026-08-07 (ledger alignment; same decision, blueprint numbering).

**Reason:** The three advisories cost ~0.04-0.04s each per freeze and none ever changed a freezing behavior in twelve weeks (measured, not assumed). Each printed a verdict nobody consumed (the D-85 lesson generalized): D-83 fires only in the "same-session" case the CEO drives anyway; D-56's zero-external NOTE restates what the diff already shows; D-89's per-file mass correlated with brief size but never blocked a freeze and duplicated the plan gate's already-harder check. The advisory carve-out in D-95's auto-approval is textually unchanged — this is retirement, not promotion. New selection rule (applies from now on): a candidate freeze-time advisory is admitted only if its blast radius (a subclass defect it would plausibly catch) exceeds its runtime and false-positive costs; a paid advisory that has produced no behavioral change is retired rather than kept to demonstrate diligence.

**Alternatives considered:** (a) Keep the advisories and make them toggle-able — rejected, three more code paths to test for no consumer; (b) only merge D-89's freeze and plan-gate halves into one scored gate — rejected, the plan gate is the only point where rejection happens and is the correct sole consumer; (c) move the rules to README prose so the history keeps the note while the pipeline drops it — rejected, docs still claim a script prints it and a docs-only claim is a lie (Rule 5); (d) apply the same measured-cost discipline to the retained hard gates — explicitly out of scope; gates that change what a violation does are stop-and-ask (Rule 3).

**Do not suggest:** Re-adding any of the retired advisories "as a light diagnostic" — none had a consumer; converting any retired advisory into a hard gate; extending `refreeze.sh` preflight count as a delivery metric; removing a hard gate because an advisory was removed.

---

## D-114 — 2026-08-02 — Frozen oracle is content-scoped, tests/-confined, and Linux-sandbox-only

**Decision:** Every production pytest entry point is explicitly confined to `tests/`. Refreeze classifies a staged test as changed only when it is new or byte-different from the tracked test. Pytest collection and the D-75 red-before-green check execute only through the Linux Podman sandbox; collection may use static AST when pre-implementation imports prevent sandbox collection, but generated tests never execute on macOS. If the red-check sandbox cannot produce a readable report, refreeze halts. D-90's host-execution fallback is retired. Separately, when a task has already consumed its brief-revision allowance, the orchestrator packages a TPM escalation before calling the EM; it does not require and validate a revised brief that it must discard.



> Ported from the blueprint 2026-08-07 (ledger alignment; same decision, blueprint numbering).

**Reason:** Testchat v75 collected 19 archived staging tests outside `tests/`, classified a byte-identical returned suite as 98 changed tests, and spent its final model call producing a schema-valid 2,631-character revised brief after the 2,500-character allowance was already exhausted. The artifact then failed validation before the existing escalation branch could run. These were scope and ordering defects: more machinery produced less useful evidence and added roughly 25 minutes to a run that completed no task.

**Alternatives considered:** Keep bare repository-root pytest and exclude known archive paths (rejected — every new directory reopens collection); compare staged tests by path presence (rejected — whole-suite TPM returns make unchanged behavior look new); retry/compress the over-cap brief (rejected — the revision cannot be consumed); execute generated tests on the Mac when Podman is unavailable (rejected — it contradicts the VM boundary and turns TPM output into host code execution).

**Do not suggest:** Restoring repository-root project pytest; treating a returned-but-identical test as changed; adding a host pytest fallback; consulting for a revised brief after its allowance is exhausted.

## D-123 — 2026-08-01 — Real container builds run on packaging changes and a weekly backstop

**Decision:** A project-owned `.github/workflows/container-build.yml` performs a pulled, no-cache Docker build when `Containerfile`, `.dockerignore`, `requirements.txt`, or the workflow itself changes; it also runs every Monday and on manual dispatch. After building, it starts the image and asserts that `/work` contains no source, tests, or Git metadata and that the temporary requirements manifest was removed. The blueprint and the actively maintained `testchat` child carry the workflow; other local children remain explicitly deferred because their stack adaptations are project-owned.



> Renumbered from D-112 on 2026-08-07 (ledger alignment): D-112 now designates the delta-mapped verdict decision back-ported from testchat; this container-build entry is D-123.



> Ported from the blueprint 2026-08-07 (ledger alignment; same decision, blueprint numbering).

**Reason:** Static checks prove that the Dockerfile no longer says `COPY .`, but they cannot prove the base image still resolves, browser installation still works, dependencies remain installable, or the finished image has the expected filesystem shape. Building on every source commit would repeatedly pay for the accepted ~1.2 GB browser layer without testing a changed packaging input. Change-scoped plus weekly provides real integration evidence at bounded cost.

**Do not suggest:** Running the expensive clean build on every source-only commit; pushing the validation image to a registry; restoring build cache to make a test named “clean build” faster; treating a successful Dockerfile parse or static grep as equivalent to a completed image build.

## D-113 — 2026-08-01 — Success cleanup recovers its prior spec from durable history

**Decision:** When the runtime task checkpoint is empty after intentional success cleanup—or partial state loss—`scripts/orchestrate.sh` resolves the prior milestone from the newest validated entry in `.pipeline-completions.json` instead of trusting a lone `.pipeline-state/spec_version`. That recovered version drives `SPEC_ADVANCED` before exact-match completions are restored and is retained separately as `delta_baseline_spec` for the entire in-progress milestone, so same-spec retries preserve every intervening delta in D-65 edit scope. Task reset and edit scope share one fail-closed affected-task computation over that range, and every in-process plan revision recomputes and reapplies it before the DAG continues. `completion-ledger.py latest` returns the newest successful spec (or zero for no history), accepts only canonical positive version keys, validates the entire ledger, and makes malformed history halt. A prior version newer than the frozen spec and a missing intervening delta also halt rather than guessing through incomplete history.



> Ported from the blueprint 2026-08-07 (ledger alignment; same decision, blueprint numbering).

**Reason:** D-108 correctly ordered restore before delta invalidation, but D-99's success cleanup deleted the runtime version used to arm that invalidation. The fallback silently set the missing prior version equal to the new frozen version, so `SPEC_ADVANCED=0`; a partial checkpoint could also retain only that version after losing every task marker. A one-file mechanical re-plan can preserve an affected task's exact fingerprint when test content changes under the same node-id; D-108 could then restore it as done and skip the affected-task reset. A first correction that considered only the newest delta still failed when more than one freeze elapsed after success; advancing runtime `spec_version` after the first reset then lost that wider range on retry. Separately recomputing D-65 scope could fail open, while caching it across a later decomposition revision made it stale. The full suite remained a backstop, but legitimate implementation work was misrouted into drift/escalation instead of reaching the coder.

**Alternatives considered:** Persist only `spec_version` inside `.pipeline-state/` after success (rejected — success cleanup must leave no runtime checkpoint that resembles a live run); infer the version from commit subjects (rejected — the tracked ledger is schema-validated and already binds successful specs); require every re-plan to change the task fingerprint (rejected — mechanical one-file planning intentionally carries unchanged briefs and same-node test mappings); rely on the full-suite drift path (rejected — fail-closed is not the same as routing work correctly).

**Do not suggest:** Trusting runtime `spec_version` when the task checkpoint is empty; using current runtime version as the edit-scope baseline after a same-spec retry; defaulting missing runtime version to the current freeze when durable history exists; accepting zero, leading-zero, or malformed ledger versions as history; considering only the newest delta when several freezes elapsed; recomputing edit scope with a fail-open branch or retaining it across a validated plan revision; restoring exact-match completions before determining whether the spec advanced; treating the final suite's eventual red verdict as proof that the task-routing defect is harmless.

## D-111 — 2026-08-01 — Accepted flakes are counted by spec and recur into a TPM escalation

**Decision:** D-77 flake-green occurrences are recorded in tracked `.pipeline-flakes.json` only after the milestone's full-suite success. Each node records its successful spec version and whether it passed one or two isolation attempts; rerunning the same spec replaces rather than increments the event. Before auto-green, the shell projects the new count. At `SWBP_FLAKE_ESCALATION_THRESHOLD` (default 3, positive integer), the suite remains red and the shell creates a recurring-flake TPM bundle directly, bypassing the generic EM drift consult. History is schema-validated, bounded to 50 spec events per node, and malformed history fails closed.



> Ported from the blueprint 2026-08-07 (ledger alignment; same decision, blueprint numbering).

**Reason:** D-77 and D-100 distinguish a one-off carried flake from reproducible drift within one run, but every later run forgot that evidence. The result could be an indefinitely unstable frozen test repeatedly excused as a new one-off. Spec-version counting is durable and idempotent; the threshold converts repeated evidence into the correct owner action. A flaky frozen oracle is a TPM test/spec defect, not an implementation decomposition problem an EM can repair.

**Alternatives considered:** Count every retry (rejected — operator reruns would inflate history); record candidates before milestone success (rejected — failed runs are not accepted flake evidence and would dirty the tree before escalation); quarantine the test (rejected — frozen acceptance cannot silently shrink); send chronic flakes through the EM first (rejected — the shell already has the decisive test-history evidence and the EM cannot edit frozen tests).

**Do not suggest:** Resetting counts at milestone boundaries; counting 0/2 isolation failures as flakes; allowing the threshold event to auto-green and merely writing a warning; letting an agent edit the ledger; using wall-clock timestamps instead of successful spec versions as the identity.

## D-110 — 2026-08-01 — Test-report compatibility exercises the real pytest plugin

**Decision:** The unconditional control-plane selftest job installs `pytest-json-report`. Selftests invoke a real pytest subprocess with that plugin, then feed its generated green and skipped reports through the production `run_tests` parser. Hand-built report shapes remain for adversarial cases, but they are no longer the only compatibility evidence.



> Ported from the blueprint 2026-08-07 (ledger alignment; same decision, blueprint numbering).

**Reason:** Synthetic JSON fixtures can remain green while a plugin upgrade changes field placement, outcome names, or summary structure. The parser decides whether code ships, so its adapter boundary must be tested against the actual producer. A passing report pins the positive path; the real skipped report pins the frozen-oracle rule that only ordinary passes are green.

**Do not suggest:** Replacing adversarial synthetic fixtures entirely (they cheaply cover rare xfail/XPASS and corrupt-report shapes); trusting pytest's process exit alone; installing the plugin only in the application-test job while the skeleton-safe control-plane job runs the compatibility test.

## D-109 — 2026-08-01 — Approval hashes exclude volatile diff timestamps

**Decision:** Every refreeze deletion diff that compares a tracked artifact with `/dev/null` supplies explicit `diff --label` values. The review output still identifies the real path and `/dev/null`, but neither header contains a filesystem timestamp. The existing end-to-end `--diff` then `--approve <hash>` tests remain the mechanical contract.



> Ported from the blueprint 2026-08-07 (ledger alignment; same decision, blueprint numbering).

**Reason:** D-107 added automatic retirement of the prior `ERD-DELTA.md`. Its unified diff used `/dev/null` directly, whose displayed timestamp changes between invocations. The approval token is the SHA-256 of that text, so an unchanged staging tree could produce a different hash seconds later and reject a valid approval. A hash-bound gate must vary only when the reviewed content varies.

**Do not suggest:** Removing the hash binding; retrying until two timestamps happen to match; omitting deletion content from the review diff; normalizing the hash after displaying different bytes to the reviewer.

## D-108 — 2026-07-30 — Successful task completions have a durable, exact-match ledger

> Amended 2026-08-01 by D-113: post-success re-freeze detection recovers the
> prior successful spec from this ledger before restoration and delta reset.

**Decision:** On a full-suite-green run, `scripts/orchestrate.sh` records every completed task in tracked `.pipeline-completions.json` before deleting `.pipeline-state/` and includes the ledger in the `[success]` commit. Each record binds the task id to its full plan-entry fingerprint, output path, and output-file SHA-256. On a later run, the shell may restore `done` markers only into an entirely empty runtime task-state and only when all three values still match; any live/partial checkpoint takes precedence. The ledger's newest successful spec replaces the runtime version erased by success cleanup (D-113); restore then runs before re-freeze invalidation, so the existing delta reset makes affected tasks pending when mapped test content changed without changing the plan entry. `SWBP_REBUILD_FROM_SCRATCH=1` bypasses restoration. The ledger retains the newest 50 successful spec versions and fails closed when malformed.



> Ported from the blueprint 2026-08-07 (ledger alignment; same decision, blueprint numbering).

**Reason:** D-99 fixed the permanent post-success halt by recognizing a covering `[success]` commit, but the success path still erased every `done` marker. The next milestone therefore knew it was safe to run yet forgot which unchanged work had already passed, contradicting D-24 resume economics and forcing needless coder calls. Git ancestry proves that cleanup was legitimate; it cannot prove that a particular current output still matches a particular completed task. The fingerprint-plus-output-hash binding supplies that missing proof without treating runtime counters, logs, retries, or escalations as durable state.

**Alternatives considered:** Preserve all of `.pipeline-state/` after success (rejected — transient counters, locks, logs, and escalation artifacts would masquerade as a live run, and operator cleanup would erase the only record); infer completion from `[task]` commits (rejected — commit subjects do not bind the current plan entry or output bytes); trust only the output hash (rejected — the same bytes can sit under a materially changed brief or test mapping); store status in `tasks/plan.json` (rejected — D-26 keeps procedural state shell-owned and the validator forbids model-authored status).

**Do not suggest:** Restoring a task when either its plan fingerprint or output hash differs; restoring over a non-empty crash checkpoint; moving retry/log/escalation state into the tracked ledger; bypassing delta-driven invalidation because a prior output hash still matches; making a malformed ledger silently authoritative.

## D-107 — 2026-07-28 — Behavioral freezes carry a fresh, checked current-change ERD

**Decision:** Every post-v1 re-freeze that changes tests, retires tests, introduces AC ids, or substantively changes contracts must stage `ERD-DELTA.md`. It has mechanically recognizable sections for changed ACs, superseded ACs, changed files, and test-to-file mapping. `scripts/check-spec-delta.py` rejects missing sections, newly introduced AC ids absent from the delta, and `contracts.changed_files` entries absent from the delta. The EM treats this file as the authoritative current-milestone slice when it explicitly supersedes standing ERD prose. A later non-behavioral freeze that refreshes `ERD.md` without a new delta consolidates the completed behavior and retires the prior delta. The EM prompt also states the already-enforced D-64 Playwright final-task rule and the empty-contract-list rule verbatim.

**Reason:** M32 carried the correct PRD and frozen tests from v67, but the selector-unlock implementation was absent from the ERD through v70. Repeated retries therefore gave the EM the same stale source. At v71, `validate-plan.py` enforced D-64 while the prompt never told the EM the rule. The final change was six removed lines and one replacement, and both MTPLX coder tasks passed first try; most elapsed work was artifact and plan repair.

**Do not suggest:** Making the delta optional; asking the EM to infer which conflicting statement is newer; relying on TPM memory instead of a cross-artifact gate.

## D-55 — 2026-07-05 — Linux dev VM boundary; D-53 partial reversal for cross-boundary model access

**Decision:** Conductors move inside a persistent Lima VM (Ubuntu 24.04, virtiofs mount of `~/dev`). The VM is the structural boundary that replaces advisory conductor constraints; agents run with permissions bypassed because the VM is the containment. `orchestrate.sh` refuses to run on macOS (`uname -s` check, hard halt). D-30 Podman lanes run unchanged inside the VM as native rootless containers — same nesting depth as the previous `podman machine` arrangement on the host.

**D-53 partial reversal (cross-boundary model access):** D-53 moved LLM calls host-local precisely because cross-boundary port wiring caused the failures of the first three supervised runs. The VM boundary reintroduces cross-boundary access: `SANDBOX_LLM_HOST` (default `localhost`, set to `host.lima.internal` in the VM) parameterizes the endpoint in `llm-call.sh` and `orchestrate.sh`. This is accepted as the cost of the VM boundary. A round-trip smoke test (`llm-call.sh` with a trivial prompt, assert non-empty reply) runs in `orchestrate.sh` pre-flight to catch plumbing bugs — the class of failure that was invisible to static review and caused the misdiagnosed "model hallucinations" in early runs (correction log 2026-07-03).

**Alternatives considered:** keeping conductors on the host with advisory constraints (failed — testchat M4 proved frontier conductors cross every advisory lane under goal pressure); Docker/devcontainer (rejected — Docker-in-Docker conflicts with D-30 Podman lanes); OrbStack (rejected — shared-kernel model, insufficient isolation for skip-permissions agents); ephemeral VMs per session (rejected — destroys `.pipeline-state` crash checkpointing D-24 and git continuity).

**Deferred:** a coder sentinel-format micro-check (send a prompt that should produce `=== FILE: ... === END FILE ===` wrapping and verify the format parses) — the current smoke test only asserts non-empty reply, which catches plumbing failures but not format mismatches between llm-call.sh and the coder extraction logic. Low urgency: the extraction already hard-fails on bad format during real tasks, so it's caught one call later.

**Do not suggest:** Running `orchestrate.sh` directly on the macOS host. Removing the `uname` pre-flight check. Using Docker instead of Podman inside the VM. Hardcoding `localhost` instead of `SANDBOX_LLM_HOST`. Skipping the round-trip smoke test.

---

## D-54 — 2026-07-05 — Spec-drift policy: the test surface is the binding spec; ERD prose is advisory design intent

**Decision:** Only what is mechanically checkable at freeze or run time is binding: the frozen test suite, `contracts.json` (entry points, routes, schemas, smoke_checks), and the gates that enforce them. ERD prose — implementation constraints, library choices, internal design notes — is advisory design intent. Code that passes the full frozen suite is conformant by definition, even where it deviates from ERD prose. Consequences: (1) the TPM must express every MUST-HOLD constraint as something observable at the locked surface — a test, a contracts entry, or a smoke_check — or accept that it is guidance, not law; (2) deviating from advisory ERD prose is not a violation, but it MUST be reported to the CEO in the run summary (silent drift is still a reporting defect under Operating Rule 4); (3) when drift accumulates enough that the ERD misleads the next milestone's TPM, the fix is a refreeze that re-trues the prose — bookkeeping, not rollback.

**Found by:** the testchat M3/M4 supervised runs (2026-07-04): shipped code replaced httpx with raw urllib reads and streamed think-content to the frontend, both contradicting frozen ERD prose (C-4, think-stripping) — with the full suite green throughout. The tests observe only the locked surface, so prose-level constraints were undetectably violated. Nothing in the pipeline can catch this class of drift, and pretending otherwise mislabels a suggestion as a rule.

**Alternatives considered:** a post-success conformance review step, human or LLM, diffing implementation against ERD prose (rejected — it is an advisory review by exactly the class of agent that the M4 incident proved ignores advisory constraints under goal pressure; it adds a cycle per milestone without a mechanical guarantee, and its failure mode is silent, which is the problem it claims to solve); making ERD prose binding by policy alone (rejected — restates the repo's founding axiom in reverse: a rule that cannot be enforced mechanically is a suggestion).

**Do not suggest:** Failing or re-running a green milestone because the implementation deviates from ERD prose. Adding a conformance-review gate without new evidence that reported-but-tolerated drift caused a real defect. Moving constraints into tests retroactively to "win" a disagreement — that is a TPM spec change and goes through refreeze like any other.

---

## D-53 — 2026-07-03 — Retire the agent harness from the execution loop: EM/coder called over bare HTTP, no tools, shell writes every artifact

**Decision:** `scripts/orchestrate.sh` no longer runs `opencode serve` or invokes agents via `opencode run --attach --agent <name>`. Instead: (1) `scripts/llm-call.sh` sends ONE completion per call directly to the local OpenAI-compatible endpoint (LM Studio) — no harness, no filesystem/tool access for the model, no memory between calls. It reads a CEO-owned role→model mapping (`~/.config/sw-dev-blueprint/models.env`, successor to the `opencode.json` agent mapping, D-41 spirit unchanged) and hard-halts on an unmapped role — never a silent substitution. It supports LM Studio's `response_format: json_schema` for schema-constrained generation, with graceful fallback to unconstrained if the server rejects it. (2) The orchestrator now gathers whatever context a call needs (ERD, contracts, test-nodeids, the prior plan, relevant failing test source) into the prompt itself and writes the model's reply to disk itself: JSON straight to `tasks/plan.json`/`diagnosis.json` for the EM, and for the coder, a sentinel-wrapped block (`=== FILE: path === ... === END FILE ===`, the same convention the TPM shuttle already uses) parsed and written to exactly the task's named path — a reply naming a different path or missing the block is a coder FAILURE (retry/consult evidence), never written. (3) `sandbox-run.sh` and the `Containerfile` drop everything OpenCode-related (the D-52 config-mount, the version-pinned install) since nothing inside the sandbox talks to a model anymore — it now runs `pytest`/`smoke_check` only, with `--network none` (no LLM to reach, so no reason for the container to have network at all — untrusted generated code gets no exfiltration path either). `opencode.json` is stripped to the conductor's own permission config (the `em`/`coder` agent blocks are deleted — nothing invokes them); it is now entirely optional, relevant only if the CEO happens to pick OpenCode as their conductor.

**Found by:** the first two supervised POC runs on the wordcount instance (2026-07-02/03). Every failure across both runs was a harness seam, never the actual pipeline logic: `opencode run --agent em` silently fell back to a default agent on a remote free-tier model when `em` was `mode: subagent` (D-52 fixed the mode, but the failure recurred); the container's pinned OpenCode build (1.15.13) had drifted from the host (1.17.12), and the version mismatch is the prime suspect for the server dropping the `--agent` selection even after D-52's mode fix; the remote fallback then hit provider rate limits. Zero of these failures were about the actual gates, lanes, or escalation ladder — every one of those fired correctly across three runs. The seam was always the harness sitting between the shell and the model, never the trust boundary itself.

**Alternatives considered:** keep tuning the OpenCode attach/agent-mode path (rejected — three consecutive fix attempts, D-40/D-52/this incident, each patched one seam and surfaced another; the pattern is the mechanism, not the configuration); swap OpenCode for a different CLI agent harness inside the sandbox (rejected — same class of seams: any harness between the shell and the model is a version to pin, a config to lose, a fallback to silently take); give EM/coder real tool access so they read files themselves (rejected — the entire value of the capability ladder is that the shell owns procedure and knows exactly what changed; tool-using agents reintroduce the "did it actually only touch its lane" question that sandboxing was built to make moot, for zero capability gain since every prompt in this pipeline is a single, boundedly-scoped question).

**Reason:** The shell already read every file these agents needed and validated every artifact they produced (`validate-plan.py`, `phase-gate.sh`, INV-4) — the harness was never load-bearing for trust, only for convenience, and it was the only thing that ever broke. A model that receives a full prompt and returns one answer needs no tools to do its job in this design; every "read X" instruction to the old agents is mechanically equivalent to pasting X into the prompt, and the shell can do that pasting without an intermediary that has its own versions, configs, and failure modes.

**Do not suggest:** Re-introducing an agent CLI/harness into the EM or coder invocation path for "richer" tool use — if a future task genuinely needs the model to explore rather than answer one bounded question, that is a signal the task decomposition (EM's job) is wrong, not that the execution tier needs tools. Hardcoding a model name anywhere to avoid the models.env mapping (violates D-41). Re-enabling sandbox network access "just in case" without a concrete test that needs it — add it deliberately, with a reason, if that day comes.

---

## D-52 — 2026-07-02 — em/coder back to primary mode; model mapping mounted into the sandbox; no silent agent/model substitution

**Decision:** Three coupled fixes from the first orchestrate run. (1) `em`/`coder` return to `mode: "primary"` in `opencode.json` — `opencode run --agent <name>` refuses subagent-mode agents ("not a primary agent"), so D-40's flip broke the orchestrator's only invocation path. Impersonation protection does not regress: the sandbox lane mounts (D-30) physically bound what each agent can write regardless of mode, and both agents keep `task: false` (D-43/D-48). (2) `sandbox-run.sh` mounts the host's global `~/.config/opencode/opencode.json` (the D-41 agent→model mapping) read-only into the container HOME, rewriting `localhost`/`127.0.0.1` to `$SANDBOX_LLM_HOST` so a mapping that points at the host LLM still resolves from inside the container; auth.json rides along if present. (3) `orchestrate.sh` hard-halts if the run log shows OpenCode substituted the default agent — before this, it silently proceeded as `build` on a default REMOTE free-tier model.

**Found by:** the first supervised POC run (wordcount): the plan phase logged `agent "em" is a subagent, not a primary agent. Falling back to default agent` and ran as `build · mimo-v2.5-free`. Nothing was running on the CEO's mapped local models; the CEO noticed and aborted.

**Reason:** The silent fallback is the worst half: pipeline work left the machine on an unchosen remote model with no actor deciding that. Halting is the only honest behavior when the invoked agent is not the one that runs.

**Do not suggest:** Re-flipping em/coder to subagent mode to hide them from the CEO's TUI (cosmetic benefit, breaks the pipeline); baking a model ID into the repo to avoid the mount (violates D-41); downgrading the substitution halt to a warning.

---

## D-51 — 2026-07-02 — Initial freeze collects node-ids statically: the v1 suite cannot import src/ that doesn't exist yet

**Decision:** `refreeze.sh` falls back to static AST-based node-id derivation (module-level `test*` functions and `Test*` class methods in `tests/**/test_*.py` / `*_test.py`) when dynamic collection yields nothing AND the failure is `No module named 'src…'`. Parametrized ids are not expanded by the fallback; the first refreeze after `src/` exists re-collects dynamically. Additionally, collection diagnostics now capture and grep BOTH streams — pytest reports collection errors on stdout, which D-50's stderr-only capture missed, leaving the exact misleading "no tests" message D-50 claimed to have retired.

**Found by:** the first supervised POC run (wordcount instance): the very first v1 freeze in template history failed at collection. This is structural, not incidental — INV-1 requires the TPM suite to exist before any implementation, so at v1 every test module's `import src.…` must fail. The initial-freeze path could never have worked; every prior instance was either migrated mid-history or hand-patched.

**Alternatives considered:** stub `src/` files at freeze time (violates lanes — no actor may write src/ outside a coder task); deferring node-id collection until after the first build (the EM's plan gate needs the ids before any coder runs); having the TPM hand-author the node-id list (unverifiable, drifts from the actual suite).

**Reason:** Static derivation is exact for the accident class the template constrains anyway (frontier-TPM-authored plain pytest functions), and self-heals to dynamic collection at the next freeze. Known limit: a v1 suite relying on parametrize-expanded ids maps them unexpanded until the v2 freeze.

**Do not suggest:** Making the AST fallback the primary collector (dynamic collection is ground truth whenever imports resolve); relaxing the "no nodeids = fail" rule — a freeze without a suite still cannot gate anything.

---

## D-50 — 2026-07-02 — Stack drift killed mechanically: content-hashed sandbox image, podman preflight, honest collection errors

**Decision:** Three fixes for the sparkv2-Issue-9 failure family (TPM picks a stack at spec time; the sandbox doesn't have it; the gate reports a misleading "pytest collected no tests"). (1) `sandbox-run.sh` tags the image with a hash of `Containerfile`+`requirements.txt` — any stack change produces a new tag and an automatic rebuild; a stale image is now structurally impossible, and manual `podman image rm` ceremony is retired. (2) `sandbox-run.sh` checks podman is actually running before anything else and says exactly what to do if not — previously it failed downstream with unrelated-looking errors. (3) `refreeze.sh` captures collection stderr instead of discarding it (`2>/dev/null` was hiding `ModuleNotFoundError` since the beginning), prints it on failure, and names the requirements.txt fix when the cause is an import error. Plus a conductor guardrail in CLAUDE.md: check staged test imports against `requirements.txt` before every freeze.

**Found by:** the second live run — the TPM chose FastAPI+httpx while the sandbox carried the previous project's stack, re-creating sparkv2's Issue 9 exactly. The first occurrence was hand-fixed in the instance and logged but never ported to the template as machinery; recurrence was guaranteed.

**Reason:** An error message that misdescribes the failure ("no tests" when the truth is "can't import") costs a debugging session per occurrence. Discarded stderr is the root sin. And rebuild-on-change must be mechanical because the actor who changes the stack (TPM, via spec) is not the actor who maintains the image (operator) — a handoff that relied on someone remembering.

**Do not suggest:** Pinning the stack in the template to avoid drift (the TPM must be free to choose per project, D-41 spirit); pruning old image tags aggressively (cheap disk, and old tags let an interrupted migration fall back).

---

## D-49 — 2026-07-02 — tpm-pack.sh defaults to stdout; conductor must relay the bundle verbatim (first live-run bug)

**Decision:** `tpm-pack.sh` now writes the bundle to stdout by default; clipboard copy is opt-in via `--clipboard` (`--stdout` kept as a no-op for compatibility). CLAUDE.md gains a conductor guardrail: when the CEO asks for the TPM briefing, run the script and reproduce its entire stdout verbatim — no summarizing, no pointing at repo files (the bundle is assembled, not hand-collectable), no "it's in the clipboard"; TPM replies pasted back go to a temp file unmodified, then `tpm-unpack.sh <file>`.

**Found by:** the first live conductor session (CEO asked for the TPM prompt; got a file reference in one attempt and a false "copied to clipboard" in another). Root cause: the script's TTY auto-detection (`[ -t 1 ]`) was built for a human at a terminal, but agent harnesses may allocate a pty — the check fired inside the subprocess, the bundle went to a clipboard call the CEO never received, and nothing instructed the conductor to relay output rather than report about it.

**Reason:** In the conductor-operated design (D-40) the primary caller of this script is an agent, not a human — defaults must serve the common caller. Auto-detection that guesses the caller's context is exactly the class of cleverness that fails silently; an explicit flag cannot misfire. The instruction-layer half exists because the script fix alone doesn't stop an agent from summarizing captured output.

**Do not suggest:** Restoring TTY auto-detection; having the conductor paraphrase or trim the bundle ("the CEO only needs the gist" — the TPM needs every byte, and the sentinel footer is load-bearing for tpm-unpack.sh). Conductor denied the task tool: no agent in this repo can spawn another

**Decision:** The built-in Build agent gets `"tools": { "task": false }` in the project `opencode.json`, completing D-43. No agent — conductor, em, or coder — can spawn any agent. The only inter-agent invocation path in the entire system is `orchestrate.sh` calling `opencode run --agent` inside the sandbox. CEO-surfaced gap: "Build hands to the orchestrator" was doc-advisory while Build held the task tool — it could have dispatched coder directly, skipping sandbox mounts and per-task gates. Residual soft path: Build running `opencode run --agent coder` via bash is not allowlisted, so it falls to the ask-prompt (= CEO alarm), subject to the D-45 glob caveat.

**Alternatives considered:** Leaving Build the task tool for utility subagents (explore-style) — rejected: the pipeline never needs it, and the utility doesn't justify keeping open the one bypass around the shell's procedural monopoly.

**Reason:** "The shell is the only actor with procedural authority" (D-26) is now enforced by configuration at every seat, not by prompt discipline. Rules that can be mechanical must be (CLAUDE.md operating-rules preamble).

**Do not suggest:** Re-enabling task for Build to "parallelize" or "speed up" anything; the orchestrator is the parallelism boundary.

---

## D-47 — 2026-07-02 — External TPM review of D-40..D-46 adjudicated: pytest/conftest hole closed, permissions hardened, honest-layer statements added

**Decision:** A frontier-LLM review of the conductor redesign produced five findings; all were verified against the tree before acting (none taken on the reviewer's word). Actions: **(1) CONFIRMED+FIXED** — `"pytest*": "allow"` plus undenied root `conftest.py` gave the conductor a zero-prompt arbitrary-code-execution path (write `./conftest.py`, run bare `pytest` unsandboxed), also loadable inside sandboxed suite runs where `.cache/` is writable (test-report forgery path). Removed `pytest*` from the allowlist (suite runs go through `sandbox-run.sh`; bare pytest now asks) and denied edits to root pytest-config files (`conftest.py`, `pytest.ini`, `pyproject.toml`, `setup.cfg`, `tox.ini`) for the conductor AND the coder. **(2) OPEN** — OpenCode glob-vs-compound-command matching is untested; caveat recorded in D-45, probe scheduled for first live session. **(3) FIXED** — D-42's conductor-relayed-diff weakening now stated in its entry. **(4) CONFIRMED+FIXED** — coder's `"**": "allow"` could override global control-plane denies depending on merge semantics; denies mirrored into the coder block, and `em` got an explicit `"**": "deny"` terminal rule (fail closed regardless of merge semantics). **(5) FIXED** — `new-project.sh` warns when multiple models are loaded and respects `SANDBOX_LLM_PORT`; stale y/N-only comments in `refreeze.sh` header and CLAUDE.md structure tree updated.

**Reason:** The pipeline's own doctrine applied to its own control plane: external review, source-verified adjudication, fixes committed per concern. Finding 1 was the exact class D-45 claims to prevent (unprompted write→execute), found by an actor who never saw this session — the review layer works.

**Do not suggest:** Re-adding `pytest*` to the conductor allowlist "for quick checks" — `scripts/sandbox-run.sh -- pytest ...` is the allowed, sandboxed way to run tests.

---

## D-46 — 2026-07-02 — Milestone sizing is TPM judgment against a fixed balance; no formula

**Decision:** Milestone cutting is the TPM's call, made per project, documented briefly in each PRD. The optimization target is fixed and two-sided: small enough that the CEO's acceptance check (D-44) catches errors before they compound — one bad milestone is the maximum blast radius; big enough to use a full freeze→build cycle well — no fragment milestones that spend a freeze/accept round-trip on trivia. No arc, ordering, or size unit is prescribed to the TPM — not even as an example: an example in role instructions anchors an LLM and becomes a de-facto formula (the CEO's own sketch — engine → connector/frontend → MVP → features — lives only here, as history, deliberately outside `TPM-ROLE.md`). Corollary: every milestone must end CEO-checkable, with acceptance depth scaling to what exists — live demo with real inputs for pre-UI milestones, hands-on prototype use once any UI exists. A milestone whose CEO check can't be described is cut wrong.

**Alternatives considered:** (a) A sizing formula (N tasks / N files / N tests per milestone) — rejected: project-dependent; a formula would be gamed or fought rather than judged. (b) CEO cuts milestones — rejected: sizing requires estimating what the pipeline can deliver in one spec, which is technical judgment; the CEO states outcomes and accepts results.

**Reason:** CEO-stated doctrine (2026-07-02): balance early error detection by human user-testing against per-cycle throughput; "a TPM can intelligently figure this out; there is no formula ideally, and it depends on project." Resolves the D-44 tension for backend-only milestones (nothing hands-on to test) via scaled acceptance instead of forbidding them.

**Do not suggest:** Adding numeric sizing thresholds to gates or schemas; milestones that end at internal refactors with no CEO-observable behavior.

---

## D-45 — 2026-07-02 — Conductor bash allowlist: pipeline scripts + read-only git; everything else asks

**Decision:** The Build (conductor) session's bash permission in `opencode.json` becomes an allowlist — the pipeline scripts (orchestrate, bootstrap, new-project, tpm-pack/unpack/agent, sandbox-run, check-drift), read-only git (`status`/`log`/`diff`/`show`), pytest, and read-only file commands are allowed; `refreeze.sh` stays `ask` (D-42); **everything else falls to `ask`**. Combined with the playbook rule, this gives the non-technical CEO a decision procedure requiring zero code judgment: the only prompt you expect is refreeze-approve; any other prompt = alarm = deny and ask the conductor what it wanted.

**Alternatives considered:** (a) Default-allow bash (previous state) — rejected: bash bypasses `permission.edit`, so a conductor could `sed -i` protected files without any prompt. (b) Default-deny — rejected: the conductor legitimately needs incidental commands (installing a dep the CEO approved, starting the app for UAT); `ask` keeps those possible with the human in the loop.

**Reason:** Closes the routine accident surface of D-40's honest caveat (conductor bash outside the sandbox) while keeping fail-closed backstops (hooks, manifests) as the guarantee against what slips through. OpenCode permission enforcement remains soft (D-24/D-39); this is friction + visibility, not a wall. **Unverified assumption (Rule 6, flagged by D-47 review):** whether OpenCode matches these globs against parsed sub-commands or the raw command string is untested — if raw-string, `scripts/bootstrap.sh && <anything>` would pass as allowed. Probe this in the first live conductor session before trusting the allowlist; until then treat it as friction only.

**Do not suggest:** Widening the allowlist with write-capable commands (`sed -i`, `rm`, `git push`, `pip install`) to reduce prompts; those prompts are the point.

---

## D-44 — 2026-07-02 — The CEO gate is outcome acceptance, not diff review; refreeze approval reframed as authorization

**Decision:** The CEO does not review code or diffs — ever. The refreeze approval (terminal y/N or D-42 hash prompt) is redefined as **authorization**: "this delta is a change I asked for," verified by matching the TPM's plain-language description against the CEO's own request. The technical scrutiny of a delta is entirely mechanical and pre-approval: INV-4 surface check, contracts schema validation, hash binding. The CEO's real quality gate moves to the end of every milestone: **user-test the running prototype** (conductor launches it; CEO uses it like a real user). Definition of Done gains this as its one judgment item: orchestrate exit 0 = built-as-specified; CEO acceptance = built-right. A green suite that fails CEO acceptance is a spec defect → back to the TPM, not a code fix.

**Alternatives considered:** (a) CEO reads every diff (original D-31/D-42 framing) — rejected: not meaningful for a non-technical CEO; a signoff that can't distinguish good from bad diffs is theater and trains rubber-stamping. (b) A second LLM as diff reviewer — rejected for now: adds an unaccountable layer whose review is itself unverifiable self-report; may be revisited as a separate decision.

**Reason:** Matches the actual operator (CEO checks outcomes, not codebases) and the agile cadence: milestones are the checkpoints, prototype acceptance is the check. Aligns the gate's claimed meaning with its real meaning — the system's honesty principle applied to its own front door.

**Do not suggest:** Skipping the UAT step because tests are green; treating CEO acceptance as optional for "internal" milestones (every milestone ends at something the CEO can try — if it doesn't, the milestone was cut wrong).

---

## D-43 — 2026-07-02 — Flat hierarchy under the shell: `em`/`coder` denied the task tool

**Decision:** Both subagents get `"tools": { "task": false }` in `opencode.json`. The orchestrator invokes EM and coder independently, as direct reportees; neither agent can spawn any other agent. The EM "manages" the coder exclusively through `tasks/plan.json` — its briefs are the management; the shell delivers them, gates each result, and owns retries.

**Alternatives considered:** EM-drives-coder (the org-chart intuition the names suggest) — rejected: coder would run inside EM's sandbox context (wrong write lane), the per-task gate and mapped-test run between tasks would be skipped, escalation counters would drift, and the task tool is the known OpenCode permission-bypass route (issues cited at D-24/D-39).

**Reason:** No LLM should sit in the reporting chain of another LLM — every inter-agent handoff must cross a deterministic checkpoint (D-26). Advisory "EM never drives" becomes mechanical.

**Do not suggest:** Re-enabling the task tool for either subagent to "streamline" plan execution; having the conductor invoke coder directly around the orchestrator.

---

## D-42 — 2026-07-02 — Refreeze approval without a terminal: `--diff` / `--approve <hash>` behind the OpenCode ask-prompt

**Decision:** `scripts/refreeze.sh` gains two non-interactive modes so the conductor (D-40) can drive freezes while the human stays the gate. `--diff` validates the staging dir, prints the full diff plus its `DIFF-SHA` (sha256 of the diff text), and applies nothing. `--approve <sha>` recomputes the diff and proceeds only if the hash matches; `opencode.json` marks `scripts/refreeze.sh *` as `bash: ask`, so the CEO's click on that prompt — whose command line carries the hash of the diff they just read in chat — IS the approval. Any change to staging between review and approval changes the hash and fails closed. The interactive y/N path is unchanged and remains the fallback.

**Alternatives considered:** (a) Keep terminal-only y/N — rejected by CEO direction (no command running). (b) Honor-string approval ("CEO said yes in chat") — rejected: no binding between what was read and what is applied. (c) A `--yes` flag — rejected: approves whatever staging contains at run time, not what was reviewed.

**Reason:** The gate's essence is "a human read THIS diff and approved THIS diff." The hash preserves that binding without a TTY. Honest layer statement: the ask-prompt depends on OpenCode's permission enforcement (soft, see D-24/D-39 caveats); the backstops remain the hash binding itself, the pre-commit hook, and the frozen-manifest verification failing closed on every gate run. **Known weakening vs terminal y/N (D-47 review):** the CEO sees the diff only through the conductor's relay — a misreporting conductor could display doctored diff text alongside the true hash of different staged content, and the prompt would look right; the tty path showed the script's own output on a trusted channel. The raw diff is always at `.pipeline-state/refreeze-pending.diff` for direct reading, the terminal path remains for structural freezes, and the blast radius of an unread-but-authorized delta is one milestone, caught at UAT (D-44). Accident-class threat, accepted; not zero.

**Do not suggest:** Adding `--yes`/`--force`; letting the conductor summarize the diff instead of printing it in full; approving on a stale hash after restaging.

---

## D-41 — 2026-07-02 — Model identity leaves the repo: the blueprint is model-agnostic

**Decision:** No file in the template or its instances names an actual LLM (no model IDs in `opencode.json`, scripts, or operative docs). The repo's `opencode.json` defines roles, prompts, modes, and write lanes only. The CEO maps agents to models in the global `~/.config/opencode/opencode.json` (OpenCode merges global + project config) and loads whatever they choose in LM Studio; pre-flight probes discover the loaded model via `GET /v1/models` instead of asserting a name. The blueprint constrains model *class* only: TPM frontier-tier, EM mid-tier, coder local non-thinking (Hard Rule 1 stays, expressed class-wise).

**Alternatives considered:** (a) Keep pinned models with placeholders like `[EM_MODEL]` — rejected: placeholders leak into instances unfilled (see sparkv2) and every model swap dirties the repo. (b) Env-var indirection in the repo config — rejected: still couples the repo to a naming scheme.

**Reason:** Model choice is an operator preference that changes weekly; the pipeline's guarantees come from gates and frozen tests, not from any particular model. Hardcoding created recurring drift between what docs claimed and what was actually loaded (SANDBOX-VALIDATION.md records four different models in one week).

**Do not suggest:** Re-adding model IDs to the repo "for reproducibility" — record the model used for a given run in session notes if it matters, not in the control plane.

---

## D-40 — 2026-07-02 — OpenCode Build agent as conductor; `em`/`coder` become subagents; CEO runs no commands

**Decision:** OpenCode is the harness AND the CEO's single interface. The built-in **Build** agent is the conductor: the CEO talks to it in business language; it runs `new-project.sh`, the TPM shuttle scripts, `refreeze.sh --diff/--approve` (D-42), and `SANDBOX=1 scripts/orchestrate.sh`, then reports results. `em` and `coder` flip to `"mode": "subagent"` — machine-invocable (task tool / `opencode run --agent`), no longer Tab-cycled by a human. Procedural authority does NOT move: `orchestrate.sh` still owns the DAG, gates, counters, and escalation (D-26); Build launches it and interprets exit codes, nothing more. Project-level `opencode.json` denies the Build session edits to `tests/`, `scripts/`, `src/`, hooks, and the control plane.

**Alternatives considered:** (a) Build re-implements orchestration conversationally — rejected: reintroduces LLM procedural authority that D-26 removed for cause. (b) Keep em/coder as Tab-cycled primaries — rejected: requires the CEO to operate the TUI, contradicting the no-commands direction.

**Reason:** The CEO's two real decisions (what to build, whether to approve a freeze) never required a terminal; everything else was operator toil. Honest layer statement: Build's edit denies are OpenCode-harness-soft (the D-24/D-39 permission caveats apply) — the hard walls remain the read-only sandbox mounts for em/coder (D-30), phase-gate manifests failing closed, and the pre-commit hook.

**Do not suggest:** Moving DAG/retry/escalation logic into Build's prompt; making the TPM an OpenCode agent (OpenCode cannot deny reads — see D-39 alternative (b)); giving Build write access to `scripts/` or `tests/` to "unblock" a run.

---

## D-39 — 2026-07-02 — Agent-mode TPM: scoped repo access via `tpm-agent.sh` (D-38(b) triggered by CEO decision)

**Decision:** The TPM may now run as a repo agent — `scripts/tpm-agent.sh` launches Claude Code with `scripts/tpm-agent-settings.json`. Containment, per the shape D-38(b) recorded: WRITE only `.tpm/outbox/` (gitignored; installed exclusively through the interactive human y/N of `scripts/refreeze.sh .tpm/outbox` — refreeze already took a staging-dir argument, unchanged); READ everything except `src/` (harness-denied), with `Bash` denied entirely so the wall cannot be bypassed via `cat`; anything outside the pre-approved lane falls to the harness's ask-prompt, which the playbook tells the CEO to treat as an alarm. The TPM triggers no procedure — orchestrate/refreeze/EM/coder runs stay operator- and shell-initiated. Chat mode (D-38 pack/unpack) remains fully supported as the fallback and the stronger air gap. The operator's imagined third job — couriering prompts from TPM to EM — is explicitly documented as nonexistent: the frozen spec is the only TPM→EM handoff, delivered by `orchestrate.sh` (D-26/D-28).

**Alternatives considered:** (a) Unrestricted repo access — rejected: reading `src/` breaks oracle independence from milestone 2 onward, and free writes re-open the incident class in TPM-ROLE.md's institutional memory. (b) OpenCode agent for the TPM instead of Claude Code — rejected for containment: OpenCode `permission.edit` globs are non-transitive (bypassable via the Task tool — opencode issues #12566/#20549, already cited at D-24); Claude Code deny rules take precedence over allows and cover Read as well as writes. (c) Podman-mounted physical wall (tmpfs over `src/`) — stronger but the frontier-agent harness cannot usefully run inside the pipeline's container; recorded as the hardening step if harness-level deny ever proves insufficient in practice.

**Reason:** The CEO explicitly chose the D-38(b) upgrade path — the operator cost of chat-mode shuttling outweighed the marginal wall-strength difference for this operator. The honest layer statement is in `tpm-agent.sh`'s header: the read wall is harness-enforced (softer than the chat air gap); the write wall is layered and hard (harness deny + ask-prompts + hash-pinned manifests failing closed + the interactive refreeze gate).

**Do not suggest:** Widening the read scope to `src/` "for better test quality" — that inverts the role's reason to exist. Letting the TPM run `refreeze.sh` or answer its prompt. Removing chat mode — it is the fallback wall and the reference trust model. Weakening the `Bash` deny in `tpm-agent-settings.json` for convenience; if the TPM needs a fact only a command can produce, the operator runs the command.

---

## D-38 — 2026-07-02 — TPM shuttle scripts (`tpm-pack.sh`/`tpm-unpack.sh`) + CEO playbook; TPM stays chat-side

**Decision:** The operator's courier burden around the chat-based TPM is automated, not the air gap. `scripts/tpm-pack.sh` assembles the complete TPM session briefing (TPM-ROLE.md, contracts schema, and the currently frozen spec + VERSION when one exists) into one clipboard blob — deliberately excluding `src/` and `tests/` (oracle independence, INV-1). `scripts/tpm-unpack.sh` splits the TPM's reply — artifacts wrapped in mandatory `=== FILE: <path> ===` / `=== END FILE ===` sentinels, format recorded in TPM-ROLE.md — into `scripts/.approved/incoming/`, validating paths against the same whitelist `refreeze.sh` enforces, fail-closed (one bad path rejects the whole reply; a non-empty staging dir requires `--force`). The trust model is unchanged: unpack only stages; the human y/N diff in `refreeze.sh` remains the only installation door. `docs/CEO-PLAYBOOK.md` documents the operator loop end-to-end.

**Alternatives considered:** (a) Repo read/write access for the TPM — rejected: read access breaks oracle independence for every milestone after the first (the TPM could derive tests from `src/`), and write access re-opens the exact incident class in TPM-ROLE.md's institutional memory (an agent quietly weakening a gate to make a run pass). (b) Scoped agent-TPM (deny-read `src/`, write only `incoming/`) — viable, deferred: harness-permission scoping is a softer guarantee than the chat air gap; revisit if shuttle friction still chafes after a few real milestones. (c) Status quo (manual file courier) — rejected: per-artifact hand-selection is error-prone in both directions, and friction the operator routinely skips is a control that doesn't exist.

**Reason:** The no-repo-access design is load-bearing; the copy-paste drudgery around it is not. Separating the two makes the safe design cheap enough to actually operate: one paste starts a milestone, one command banks the reply. On CEO-PLAYBOOK.md vs D-01: this is an operator runbook for machinery that did not exist at D-01 — it restates no diagrams or rules from BLUEPRINT.md, which is what D-01 pruned.

**Do not suggest:** Giving the TPM direct repo access (see alternative (b) for the recorded upgrade path and its trigger). Having tpm-pack include `src/` or the frozen `tests/` "for context". Letting tpm-unpack write anywhere but the staging dir, or skip its path whitelist because refreeze validates too — the double validation is deliberate (named culprit at unpack time; defense in depth at install time).

---

## D-37 — 2026-07-02 — `build_extra`/`test_extra`: exact-file lane exceptions in `.gate-paths`

**Decision:** `.gate-paths` gains two optional keys, `build_extra=` and `test_extra=` — space-separated lists of **exact file paths** outside the lane directory that the legacy `build`/`test` phases may also touch. `phase-gate.sh` filters them from the violation list with `grep -vFx` (fixed-string, whole-line): no globs, no regex, no prefix matching. Unset keys change nothing — the default gate behavior is byte-identical to before. Motivating case: a JS/TS build lane that must touch `package.json` alongside its source directory.

**Alternatives considered:** (a) Glob/regex patterns — rejected: a pattern is a scope grant whose true size is unknowable at review time; an exact filename is auditable at a glance. (b) Making the lane a path *list* instead of one directory — rejected: broader redesign of every consumer of `build_dir`/`test_dir` for a need that is, so far, one file per stack. (c) Nothing (status quo) — rejected: `.gate-paths` already exists precisely so non-default layouts don't require editing the gate; "one manifest file outside the lane" is the same class of layout fact, and without this key the only workaround is disabling the gate.

**Reason:** Closes the concrete slice of the stack-flexibility gap (flagged by the 2026-07-02 external review) that costs almost nothing to carry: directories were already configurable, but one out-of-lane manifest file (`package.json`, `Cargo.toml`, `go.mod`) had no legal path. Verified in an isolated worktree: gate still fails without the key, passes with it, and a nested `frontend/package.json` does NOT match a bare `package.json` entry — exact-match semantics hold.

**Do not suggest:** Extending `build_extra`/`test_extra` to globs, regexes, or directories — if a phase needs a whole extra directory, that is a lane redesign (alternative (b)) and gets its own decision. Adding entries to `.gate-paths` on an agent's initiative: the file is control-plane-adjacent and lane-widening is a human call (Rule 3).

---

## D-36 — 2026-07-02 — Gate-script self-tests (`scripts/selftest/`) + sandbox LLM port made configurable

**Decision:** The two Python gate scripts — `validate-plan.py` and `check-test-surface.py` — get a hermetic pytest suite at `scripts/selftest/selftest_gates.py`, run by a dedicated unconditional CI job (`selftest`, no skeleton guard: it needs no project `src/` or requirements). The file is deliberately named `selftest_` (not `test_`) so the bare `pytest` / `pytest --collect-only` runs in `orchestrate.sh` and `refreeze.sh` never collect it into the frozen suite or its node-id set; it runs only when invoked explicitly. Placement under `scripts/` keeps it agent-unwritable via the existing `--rw` refusal. Both manifests track it. Separately, `sandbox-run.sh` reads `SANDBOX_LLM_PORT` (default 1234, LM Studio) instead of hardcoding the port, matching the existing `SANDBOX_LLM_HOST` pattern (D-30 addendum).

**Alternatives considered:** (a) Integration tests for `orchestrate.sh`/`refreeze.sh` — rejected for now: shell-loop harnesses are expensive to carry, and dry runs cover them until an incident says otherwise (D-32's adopt-on-trigger doctrine). (b) A root pytest config (`testpaths=tests`) to allow normal `test_*` naming — rejected: it changes what the pipeline's bare `pytest` collects for every child, a control-plane behavior change disproportionate to the need. (c) Skipping self-tests entirely — rejected: a validator that wrongly passes fails open, and these two scripts are pure functions over JSON/file trees, so coverage is cheap to write and carry.

**Reason:** External review (2026-07-02) correctly flagged that a project whose philosophy is "tests as ground truth" had zero tests for its own gate scripts. The Python gates are the highest-value, lowest-cost slice: deterministic, subprocess-testable, and the failure mode (fail-open validation) is the worst in the gate set.

**Do not suggest:** Renaming the selftest file to `test_*.py` or moving it into `tests/` (frozen TPM lane; would pollute frozen node-id collection). Extending self-tests to the bash orchestration before an incident triggers it. Conditioning the `selftest` CI job on the skeleton guard.

---

## D-35 — 2026-07-01 — Fleet Tier 3 (versioned core distribution): designed, deliberately NOT built

**Documentation-only:** This entry records a design and its adoption trigger so it is not re-litigated each session. No code exists for it, on purpose.

**Decision:** The structural endgame for fleet distribution — template-owned scripts shipped as a versioned release artifact (`blueprint-core-vN`) with its own manifest, pulled by children as a tracked dependency, giving the control plane a provenance chain anchored outside every child — is **deferred**. Chosen shape, if/when built: release-artifact over git-subtree (cleaner provenance, no merge noise in children; the D-33 manifest split already defines exactly what the artifact would contain). **Adoption trigger, per the repo's own doctrine (D-25, D-32 — adopt on trigger, don't pre-harden):** roughly five or more active children, or the D-34 update flow demonstrably chafing (updates skipped because the diff-review burden grew, or children needing divergent control-plane versions). Until then, D-33 detection + D-34 propagation cover the only incident class that has actually occurred.

**Alternatives considered:** (a) Build it now — one active child; machinery would be maintained for years before anything needs it, and the migration of existing children (establishing spark's baseline by hand — it has no birth-SHA) is real human work with no current payoff. (b) git subtree — git-native but pollutes child history and makes partial adoption ambiguous. (c) Never — at real fleet scale, per-child diff-approval of every control-plane update stops scaling; the trigger exists because the need plausibly will.

**Reason:** Cheap-to-build is not the bar; cheap-to-carry is. Recording the shape and the trigger costs one D-entry; building it costs a distribution mechanism plus child migration, against a doctrine this repo has already paid to learn twice (D-01's bloat prune, D-04's demoted line-count gate).

**Do not suggest:** Building Tier 3 before the trigger fires. Re-opening subtree-vs-artifact from scratch when it does — start from this entry's rationale and revise with evidence.

---

## D-34 — 2026-07-01 — Template propagation: update-template.sh (the refreeze pattern, applied to the control plane)

**Decision:** Children pull control-plane improvements with `scripts/update-template.sh`: it resolves the template (a local clone via `--from`, or `gh repo clone` of the `.template-version` slug), takes the file list from the **template's** `.manifest-template` at the target ref (so files added upstream flow in), shows the human one aggregate diff, requires an interactive y/N (`--dry-run` to inspect without a tty), applies contents **and exec bits**, installs the template's manifest verbatim, advances `ref=` in `.template-version`, regenerates `.manifest-project`, runs the integrity gate as a post-apply check, and commits `[template-update <sha>]`. Files removed upstream are reported for manual deletion, never auto-deleted. `--stamp` mode retrofits a pre-D-33 child (writes `ref=` only). Same protected-artifact protocol as D-31: staged delta → human diff-approval → hash re-pin → versioned commit.

**Alternatives considered:** (a) Generalize `refreeze.sh` into one approve-delta engine serving both spec and control plane — considered and rejected: the two flows share only the approval UX (~40 lines); everything else differs (staging source, validation steps — INV-4 and node-id collection are spec-only — and post-apply actions). A forced common engine is parameter soup; a shared *pattern* with two small tools is cheaper to hold. Revisit only if a third protected-artifact class appears. (b) git subtree/submodule for `scripts/` — Tier 3 machinery; see D-35 for the trigger. (c) Auto-apply in CI — propagation into a child is a human-approved act, same reasoning as D-31.

**Reason:** This closes the documented incident class directly: the Rule 8 fix that lived only in spark until hand-ported becomes `update-template.sh` + one y. Detection (D-33) says *that* you're behind; this is *how* you catch up, with the same fail-closed integrity guarantees as every other protected write.

**Do not suggest:** Auto-applying template updates. Letting the tool delete files. Running it inside the template repo (it refuses).

---

## D-33 — 2026-07-01 — Fleet drift: birth-SHA identity, ownership-split manifests, drift detection

**Decision:** Three pieces. (1) **Birth-SHA**: `.template-version` records `repo=` (template slug) and `ref=` (template HEAD SHA at instantiation, stamped by `bootstrap.sh`, retrofittable via `update-template.sh --stamp`); `gh repo create --template` leaves no upstream link, so this is the only moment fleet identity can be captured. (2) **Ownership split**: the control-plane manifest becomes `scripts/.manifest-template` (template-owned logic — gates, orchestrator, validators, schemas, prompts, hooks, drift tooling) and `scripts/.manifest-project` (per-project adaptations under Rule 3 — `.gate-paths`, `opencode.json`, `Containerfile`, `ci.yml`, the doc layer). phase-gate verifies both, fail-closed; drift is computed over exactly the template list, so a Rule 3 adaptation is never a false positive. One-shot setup scripts are deliberately unlisted: children delete them at instantiation, and the read-only mounts (D-30) already cover them. (3) **Detection**: `scripts/check-drift.sh` does a three-way compare per template-owned file (child vs template@birth vs template@HEAD) → IN_SYNC / BEHIND (exit 2, CI warns) / LOCALLY_MODIFIED, MISSING_IN_CHILD, CHILD_ONLY (exit 1, CI fails); `.github/workflows/check-drift.yml` runs it on push and weekly, skipping itself in the template repo and unstamped children.

**Alternatives considered:** (a) No fleet story — the documented failure: the Rule 8 fix lived only in spark until hand-ported. (b) One mixed manifest plus a separate drift-file list — two lists drift from each other; ownership belongs in the manifest itself. (c) Auto-sync on drift — propagation is a human-approved act (D-34); detection and propagation stay separate so CI never rewrites a child.

**Reason:** Drift you cannot compute is drift you discover in production. The birth-SHA is cheap now and unrecoverable later; the split makes "adapted" and "drifted" mechanically distinguishable; the CI job makes a quiet child hear the template move.

**Do not suggest:** Auto-applying template changes in CI. Putting template-owned files in `.manifest-project` to silence a drift failure — that is the drift, formalized.

---

## D-32 — 2026-07-01 — INV-4: test-visible surface ⊆ ERD-locked surface (lowest-confidence gate)

**Decision:** New invariant, same class as INV-1/2/3. Whatever the frozen tests observe is de-facto locked, whether or not the ERD meant to lock it — so the two locks are kept aligned mechanically: `scripts/check-test-surface.py` statically checks that tests import only `contracts.entry_points` entries (`module` or `module:symbol`) and exercise only declared `contracts.routes` path templates (segment-wise match, `{param}` wildcards). It runs inside `scripts/refreeze.sh` on the merged preview (current frozen tests + incoming delta), BEFORE the human approval prompt — a TPM test that reaches past the contracts is rejected before it can be frozen, and before it can silently shrink the EM's design space.

**Confidence flag — read this before trusting it:** this is the **lowest-confidence mechanism in the gate set**, and deliberately so. It is a grep-level static check (regex on imports and client-verb calls), in the same spirit as INV-3's grep. It catches the accident class — the test author is a frontier model following instructions, not an adversary — and does not catch dynamic imports, computed paths, or indirect observation. Tighten it from incidents per the correction-log habit; do not pre-harden speculatively.

**Alternatives considered:** (a) No check — the seam rule ("TPM locks contracts, EM owns the rest") becomes decoration the first time a test asserts on an internal. (b) AST-based analysis or import-hook enforcement at test runtime — heavier machinery than the failure class justifies today; adopt only after the crude check demonstrably misses real incidents. (c) Generating test fixtures from contracts so tests physically cannot reach elsewhere — the strongest form; noted as the escalation path if (b)'s trigger fires.

**Reason:** INV-4 is what makes the seam rule real: the EM owns everything inside the locked surface only if nothing outside the contracts can fail a build.

**Do not suggest:** Treating INV-4 as a security boundary. Loosening it by allow-listing individual violations instead of locking the surface properly in contracts.json.

---

## D-31 — 2026-07-01 — Versioned re-freeze: frozen spec changes only via human-approved delta

**Decision:** The TPM's artifacts (PRD.md, ERD.md, contracts.json in `scripts/.approved/`; the test suite in `tests/`) are hash-pinned by `scripts/.approved/frozen-manifest` and verified by **every** phase-gate run, fail-closed. They change through exactly one path: `scripts/refreeze.sh`. The operator stages the TPM's delta (full new content of only the changed files) under `scripts/.approved/incoming/`; refreeze shows the human the complete diff, requires an interactive y/N (this diff-approval IS the approval gate — it also replaces the old `Status: Approved` honor-string for the initial freeze), applies, re-collects test node-ids in the sandbox, writes `DELTA-vN.json` (changed contract ids + changed/removed test node-ids), bumps `VERSION`, regenerates the frozen-manifest, and commits `[refreeze vN]`. On the next run the orchestrator resumes **only the affected subtree**: the stale plan is re-derived by the EM, unchanged task entries keep their done status via fingerprints, and `validate-plan.py --affected DELTA-vN.json` additionally resets tasks whose mapped test content changed under an unchanged entry (plus transitive dependents). Escalated/blocked tasks get a fresh chance under the new spec.

**Alternatives considered:** (a) Frozen-forever spec — the repo's own history shows what boxed-in agents do against an unsatisfiable oracle (a gate was once quietly weakened to force a pass); wrongness needs a protocol, not a workaround. (b) Silently mutable spec — the pre-D-08 freeze-trap failure, where a re-plan architect overwrote the approved contract. (c) Approval recorded as a status string an agent can write — the original LOW-severity hole; an interactive tty prompt on a diff is not agent-forgeable through any lane. (d) Full re-run after every delta — wastes the completed subtree; the delta file exists precisely to compute the minimal reset.

**Reason:** This threads both historical failure modes: no silent mutation (agents physically cannot write the frozen artifacts — D-30 mounts + manifest check), and no dogmatic freeze (a bounded, versioned, human-approved revision path exists, and the `[refreeze vN]` commit is the durable record of every TPM round-trip).

**Do not suggest:** Letting any agent stage or apply a delta. Skipping the interactive prompt for "trivial" deltas. Editing files under `scripts/.approved/` or `tests/` directly — the next gate run fails closed on the manifest.

---

## D-30 — 2026-07-01 — Sandbox flip: read-only repo + per-lane rw mounts; pre-commit hook for the human path

**Decision:** `scripts/sandbox-run.sh` mounts the repo **read-only** and grants write access per-lane via `--rw <relpath>` (coder: build lane only; EM: `tasks/` only; test runs and smoke checks: `.cache/` only or nothing). `--rw` refuses `scripts/`, `.git/`, and `.githooks/` unconditionally — the control plane is never agent-writable. The agent user's HOME moves to a container tmpfs (OpenCode/pip session data must not live in the read-only repo). For the interactive/human entry point, `.githooks/pre-commit` enforces the active pipeline phase (from `.pipeline-state/phase` + `task_target`) and always verifies the control-plane manifest and the frozen spec; `bootstrap.sh` sets `core.hooksPath=.githooks`.

**Alternatives considered:** (a) Keep the whole-repo rw mount and rely on phase-gate detection — a prior external review demonstrated a one-phase gate-neutralization: an agent could rewrite `phase-gate.sh` plus the manifest inside its phase, and the post-phase check would execute the compromised gate. Detection-after loses to a writable detector. (b) Per-file rw mounts for the coder — Podman bind-mount granularity makes single-file mounts brittle for files that don't exist yet; lane-level mount + the `task` gate's exactly-one-file check gives the same guarantee. (c) Overlay/copy-on-write sandboxes — heavier machinery for the same property.

**Reason:** Prevention beats detection where prevention is one flag. INV-2 violations and gate-tampering become physically impossible on the orchestrated path; the gate remains as backstop for the path mounts cannot cover (a human driving directly). The control-plane manifest finally has its out-of-band anchor: the only writers of `scripts/` are the human and CI.

**Do not suggest:** Re-widening the mount to the whole repo for agent convenience. Allowing `--rw scripts/...` for any phase. Removing phase-gate because the mounts "already handle it" — the hook path and defense-in-depth are why it stays.

---

## D-29 — 2026-07-01 — Escalation ladder with batched, filesystem-only TPM round-trips

**Decision:** Escalation is a shell-owned ladder with every counter in `.pipeline-state/`: task retry (strike 1, failure evidence appended to the same brief) → EM consult at two strikes (schema-bound verdict) → `brief_wrong` (revised brief, max 2 per task) → `decomposition_wrong` (plan re-emit, re-validated, max 2 per run) → `contract_or_test_wrong` / caps exhausted / spec drift → **batched TPM bundle** → human applies the TPM's delta via `scripts/refreeze.sh` → affected subtree resumes. PRD-ambiguity escalates from the TPM to the CEO in chat. Because the TPM is a human-operated web chat (not a callable service), the shell packages each escalation as a self-contained copy-pasteable bundle (`.pipeline-state/escalations/<id>/bundle.md`, aggregated into `BATCH.md`), keeps driving every independent subtree to its own stopping point first, and halts exactly once with exit code 2. Format: `docs/ESCALATION.md`.

**Alternatives considered:** (a) Halt-and-ping on first escalation — one browser round-trip per defect; with N independent seam problems that is N round-trips instead of 1. (b) An API integration to the frontier model — assumes a service the operator does not run; the filesystem is the only integration that exists. (c) Let the EM decide when to escalate — escalation is procedure, and procedure is shell-owned (D-26).

**Reason:** Judgment escalates exactly one tier per rung, every rung is bounded, and the expensive rung (human + frontier) is batched. The bundle must be self-contained (task entry, evidence, EM diagnosis, referenced contract entries, failing frozen-test sources) because the TPM has no repo access.

**Do not suggest:** Escalating straight to the TPM without an EM diagnosis (the diagnosis is what makes the bundle actionable). Unbounded brief revisions. Letting an agent write into `.pipeline-state/escalations/`.

---

## D-28 — 2026-07-01 — Oracle projection: EM schedules frozen TPM tests, authors nothing

**Decision:** Test authorship lives at the TPM tier, frozen via re-freeze (D-31). The per-task acceptance signal of the hot loop is a **projection** of that frozen oracle: each plan task lists the frozen test node-ids expected to pass once it and its dependencies are done. The EM schedules tests onto tasks; it never authors acceptance. The plan gate enforces the mapping is total and exactly-once. Feature completion is the delta's dependent set green: the verdict run re-executes the union of every mapped node-id (D-112 supersedes this entry's "FULL frozen suite" completion clause). The case "every task passed its projection but the verdict run is red" is mechanically detected as **spec drift** and routes EM→TPM (decomposition fix or spec delta) — never to coder retries. Tasks with no covering test carry an explicitly non-oracular `smoke_check`; the validator rejects tasks with neither.

**Alternatives considered:** (a) EM authors per-task acceptance checks — re-creates oracle-authorship at the mid tier, the exact hole this redesign exists to close (the green signal must not be authored below the judgment tier). (b) Run the full suite after every task — most failures would be absent-dependency noise, drowning the real signal. (c) No per-task signal, only the final suite — failure attribution collapses; every defect surfaces at integration.

**Reason:** The working oracle of the loop and the truth oracle are the same artifact viewed through a schedule, so they cannot drift in content — only in scheduling, which the exactly-once mapping check and the drift signal both catch mechanically. INV-1 ("tests derive from the spec, not the code") is now structural rather than advisory: the tests are written before the code exists, by a tier that never sees the implementation, and no agent can edit them.

**Do not suggest:** Letting any agent author or edit tests. Treating a task's mapped-tests-green as feature-done. Routing a spec-drift signal to the coder.

---

## D-27 — 2026-07-01 — Capability ladder: TPM (web-chat frontier) / EM (mid-tier) / coder (local); test-runner agent deleted

**Decision:** The four-role pipeline (pm/architect/build/test agents) is replaced by a capability ladder matched to task type. **CEO** (human): business intent. **TPM** (frontier LLM in a human-operated web chat, outside OpenCode): PRD, ERD with machine-readable contracts, and the test suite — the smallest, highest-leverage artifacts — installed and frozen via `scripts/refreeze.sh`. **EM** (mid-tier free online LLM, OpenCode agent `em`): decomposition and diagnosis only, per D-26. **Coder** (local LLM, OpenCode agent `coder`): one file per task, pure execution. The pm/architect/build/test prompts and the test agent are deleted; tests are RUN by the orchestrator via `pytest --json-report` — a shell command needs no agent wrapped around it (Rule 5: an LLM whose job is to run a command and describe the output can only add error).

**Alternatives considered:** (a) Keep architect as a local agent — decomposition against locked seams is mid-tier work, but plan-sized judgment (contracts, tests) is not; splitting TPM/EM matches each artifact to the cheapest tier that can own it. (b) Keep a test agent to run pytest — deleted for the Rule 5 reason above. (c) All-frontier — forfeits the cost model; the ladder exists to spend frontier tokens only on spec/contract/test artifacts and escalation deltas.

**Reason:** Frontier pays per token and never stops; local is a fixed cost trending better. The ladder bets on that trendline while keeping every load-bearing artifact (contracts, tests) at the judgment tier and every procedure in shell. The seam rule: the TPM locks cross-component contracts (cheap for it, catastrophic when wrong below); the EM owns everything inside them.

**Do not suggest:** Re-adding a test-authoring or test-running agent. Giving the EM a write lane beyond `tasks/`. Calling the TPM programmatically (it is a human-operated chat; see D-29).

---

## D-26 — 2026-07-01 — Schema-validated artifact handoffs; plan.json validation gate

**Decision:** Every inter-tier handoff is a schema-validated artifact on disk; the shell orchestrator is the only actor with procedural authority. The EM's sole channel of authority is `tasks/plan.json` (schema: `scripts/schemas/plan.schema.json`), mechanically validated by `scripts/validate-plan.py` before any coder runs: one file per task and one task per file (structural atomicity), acyclic DAG, exact bijection with the frozen ERD file inventory, every frozen test node-id mapped to exactly one task, every referenced contract id present in the frozen contracts, plan freshness against `scripts/.approved/VERSION`. The plan carries **no status field** — the validator rejects one. Task status, ordering, completion, and escalation counters live in `.pipeline-state/`, owned by the shell. EM consult responses are likewise schema-bound (`scripts/schemas/diagnosis.schema.json`, verdict enum `brief_wrong | decomposition_wrong | contract_or_test_wrong`).

**Alternatives considered:** (a) EM reports decomposition and progress conversationally, orchestrator parses prose — trusts narration, the exact failure class this project exists to reject. (b) EM drives the loop itself and self-reports completion — re-creates the pre-D-05 failure (LLM forgets gates, miscounts strikes) one tier up. (c) Full `jsonschema` dependency — validator is stdlib-only (`json`/`hashlib`) to match the orchestrator's existing pre-flight contract.

**Reason:** A bad decomposition must fail loudly at validation time, not surface three phases later as an integration error. This is D-05 (deterministic shell owns procedure) applied uniformly: LLMs produce content, shell computes everything computable — so the EM's residual authority is exactly the content of its decomposition and diagnoses, nothing procedural.

**Do not suggest:** Adding a status/progress field to plan.json for the EM to maintain. Letting any agent update `.pipeline-state/`. Parsing EM free-text instead of the diagnosis schema.

---

## D-25 — 2026-06-26 — INV-3: Decision traceability gate (Adoption 3)

**Decision:** Every non-documentation decision in DECISIONS.md (tagged with a D-NN ID) MUST appear in ARCHITECTURE.md. The architect→build handoff is mechanically blocked by `scripts/phase-gate.sh architect` — the gate greps ARCHITECTURE.md for each D-ID and exits non-zero if any are missing. Documentation-only decisions are exempted via a `**Documentation-only:**` marker in the decision body.

**Rationale:** This is INV-3, same class as INV-1 and INV-2 — a mechanical, blocking gate. It closes the gap where an architect could make a decision in DECISIONS.md that never reaches the build agent (ARCHITECTURE.md is the build agent's source of truth). The grep is intentionally simple — no manifest, no registry, just string matching. This keeps the ceremony low enough that the gate is a net time-saver (catches forgotten updates) rather than a tax.

**Alternatives considered:** (a) A separate decision-manifest file — extra indirection, more things to keep in sync. (b) Requiring D-IDs in the build prompt verbatim — over-constrained, the prompt already references ARCHITECTURE.md. (c) No gate, rely on architect discipline — advisory only, contradicts the project's mechanical-gate philosophy.

**Do not suggest:** Central registry of D-IDs (the headings ARE the registry). Making the gate check for coverage in the build prompt instead of ARCHITECTURE.md.

---

## D-24 — 2026-06-26 — File-based pipeline state persistence (Adoption 2)

**Decision:** All pipeline loop state (iteration count, re-plan count, failure signature, repeat counter, current phase) is written to `.pipeline-state/` files before each agent phase. On crash, the orchestrator resumes by reading these files. `.pipeline-state/` is gitignored — runtime diagnostics only.

**Alternatives considered:** (a) Pass state via git commit messages and re-parse them — fragile, human-hostile format. (b) Store in environment variables passed to a supervisor — doesn't survive container restart. (c) Ephemeral shell variables (current design) — lost on crash.

**Reason:** A crash mid-loop (Podman OOM, network drop, host reboot) currently loses all state. The state file is a single checkpoint written BEFORE each phase, surviving anything short of `rm -rf .pipeline-state/`. Also the foundation for the OpenHands port, where the orchestrator will be an LLM agent that reads/writes files instead of shell variables.

**Do not suggest:** Version-controlling `.pipeline-state/` (ephemeral diagnostic data). Using a database, Redis, or any networked state store. Writing state after the phase (loses info on crash mid-phase).

---

## D-23 — 2026-06-26 — Fresh context per task (Adoption 1)

**Documentation-only:** This decision documents a design principle already satisfied by the shell-orchestrator architecture.

**Decision:** The orchestrator MUST spawn each build and test task in a clean context window. State transfers between tasks via structured files on disk, never via conversation history.

**How the shell orchestrator satisfies this:** `scripts/orchestrate.sh` wraps each agent phase in a separate `opencode run --attach --agent <name>` invocation (line 79-81). Each invocation starts fresh. The orchestrator itself is a shell script — no LLM context to rot.

**Target for OpenHands port:** When the orchestrator becomes an LLM agent, the coordinator loop must stay under 40% of its context budget.

**Do not suggest:** Passing state between phases as part of the agent prompt. Merging the orchestrator loop into a single agent context window.

---

## [DATE] — [Your first decision here]

**Decision:** [e.g. Using raw SQL over ORM]
**Alternatives considered:** [e.g. SQLAlchemy, Tortoise ORM]
**Reason:** [e.g. Query complexity made ORM unreadable for our join-heavy patterns]
**Do not suggest:** Switching to an ORM. This was deliberate.

---

## [DATE] — Monorepo structure (template placeholder — skip D-ID assignment)

**Decision:** Single repository for all services.
**Alternatives considered:** Separate repos per service.
**Reason:** Team size doesn't justify the overhead of managing multiple repos. Shared code is easier to refactor.
**Do not suggest:** Splitting into microservices repos until team grows past 5 engineers.

---

## D-08 — 2026-06-09 — AC9 compliance: mandatory sandbox + freeze trap closure

**Decision:** Two changes for temp PM review compliance:

1. **AC9 (no sandbox override):** Removed the `I_UNDERSTAND_UNSANDBOXED` override entirely. `orchestrate.sh` now fails immediately if `SANDBOX != 1` — no fallback path, no debug flag. Containerized execution is mandatory.
2. **Freeze trap (P3 fix):** Moved `ARCHITECTURE.approved.md` from `docs/` (architect's writable lane) to `scripts/.approved/` (outside every agent's whitelisted directory). The orchestrator creates the directory and copies the file after the architect gate passes; no agent can touch it.

**Reason:** The frozen AC9 criterion specified no env var or flag that disables containerized execution. The `I_UNDERSTAND_UNSANDBOXED` override existed as a conversational suggestion from the PM during code review but violated the frozen spec. Debug frequency is low enough that the friction is negligible — strict compliance avoids the "advisory safety" pattern the project exists to reject. The freeze trap was exposed by an empirical test: a re-plan architect could and did overwrite `docs/ARCHITECTURE.approved.md` because `docs/` is the architect's permitted directory. Moving the file to `scripts/.approved/` makes the constraint structural (wrong lane) rather than rule-based (gate carve-out).

**Do not suggest:** Re-adding `I_UNDERSTAND_UNSANDBOXED` or any sandbox-disable flag. Moving `ARCHITECTURE.approved.md` back to `docs/`. Both were deliberate removals against verified defects.

---

## D-22 — 2026-06-07 — INV-2 gate: halt, not auto-clean (reaffirmed)

**Decision:** The INV-2 gate exits with code 1 on any boundary violation (build writes tests/, test writes src/). It does not auto-clean, retry, or continue. A boundary violation is a signal for the human keystone — evidence that the instruction or model is wrong — not noise to sweep.

**Reason reaffirmed after:** A prior session softened the gate to cleanup+continue, which silently swallowed violations. The build agent wrote to tests/ (correctly detecting), the gate auto-swept it, and the run continued as if nothing happened. That defeat is why the halt exists. The cost of a halted run is the cost of INV-2 working correctly.

**Do not suggest:** Re-softening to cleanup+continue without PM sign-off.

> Add new decisions above this line, newest first.
## D-21 — 2026-06-07 — Operating Rules: rationale per rule

**Documentation-only:** This entry documents rationale for Operating Rules; it does not change the API or build plan.

**Rule 1 (report against the tree):** A hallucinated "6 commits" and an undisclosed model swap each cost a full PM review cycle to catch. The marker file makes the ref retrievable outside conversation history.

**Rule 2 (one commit, one concern):** A safety-rule change (gate halt→cleanup) was bundled with prompt edits and a pip fallback in a single commit, bypassing review. Bundling is how serious changes slip through.

**Rule 3 (stop-and-ask on constraint changes):** The gate soften was treated as routine de-blocking. Changing what happens on violation is a process decision, not a fix.

**Rule 4 (conditionals are checkpoints):** The `-ud-mlx` fallback was used silently despite its precondition (base model failure) never occurring. The swap was only caught in post-hoc review.

**Rule 5 (read the artifact):** A validation report was written from the build agent's chat summary, not from the committed artifact. The summary was less accurate than the file it described.

**Rule 6 ("detected" ≠ "enforced"):** A standalone gate-test result was placed under a live-run section, implying the pipeline enforced a boundary that was switched off at the time.

**Rule 7 (decide trivial calls):** A placement question (where in AGENTS.md to put the Reporting section) burned three turns when the PM had already stated "put it where process docs live." Re-asking after the principle is clear wastes cycles. Asking is not failure when correctness is at stake — that's the second clause of the rule.

---

## D-20 — 2026-06-07 — Advisory vs mechanical enforcement

**Decision:** Of the seven Operating Rules, only Rule 1 ("report against the tree") has a mechanical backstop — `docs/.pm-last-review` for the ref plus the PM's source-side reconciliation as the ultimate check. Rules 2–7 are advisory: they rely on PM review for enforcement and no agent workflow enforces them mechanically.

**Documentation-only:** This decision documents a process observation; it does not change the API or build plan.

**Reason:** Honest labeling prevents these rules from being mistaken for guarantees. The durable safeguard is the PM's verification, not the doc. Aspirational claims that a rule "prevents" or "ensures" something erode trust when inevitably violated.

**Do not suggest:** Claiming mechanical enforcement where none exists; adding commit-scope hooks or other automated enforcement without a separate PM decision.

---

## D-19 — 2026-06-07 — docs/.pm-last-review: PM-owned ref marker

**Decision:** Introduced `docs/.pm-last-review` — a one-line file holding the last PM-reviewed commit hash. The build agent reads it at report time to scope its commit list; no agent writes or advances it. "Reviewed" means verified and accepted by the PM — not pushed, not agent-declared done. This is the same artifact-over-memory principle the project enforces on tests (PRD → tests, never src → tests), applied to reporting: the marker removes the retrieval failure (ref buried in chat), but the PM's source-side reconciliation remains the actual guarantee.

**Alternatives considered:** (a) Storing the ref in the build agent's session/context — proven unreliable, this entire fix is why. (b) Tagging the repo with each review — noisy and requires push permissions. (c) Reading the ref from a PM-API call — overengineered.

**Reason:** The previous design relied on the PM's ref persisting in conversation history across turns. It didn't. A file in the repo is persistent, versioned, and readable by tool calls. The PM advances it only after verifying the work. The file assists, it doesn't replace the human check.

**Do not suggest:** Any agent writing to this file; removing the PM's source-side reconciliation because the file exists.

## D-18 — 2026-06-07 — 32K context as pinned default for local model

**Decision:** Confirmed the 32,768 token context length as the pinned operational setting for `qwen/qwen3.6-35b-a3b`. Measured the largest agent payload at ~3,000 tokens (test agent prompt + instruction + opencode system preamble). 32K provides 10x headroom for conversation history.

**Alternatives considered:** (a) 8,192 (LM Studio default) — caused context-length errors in prior runs. (b) 131,072 or 262,144 (model max) — unnecessary GPU memory consumption, model seats 32K at 35.16 GiB.

**Reason:** The model natively supports 262,144 tokens (`max_position_embeddings` confirmed via HuggingFace config). 32K is a comfortable operating point that leaves GPU memory headroom (35.16 GiB used across the available 128 GiB). No prompt trimming needed — the bottleneck was LM Studio's default.

**Do not suggest:** Lowering context below 32K; raising to 256K without a demonstrated need.

---

## D-17 — 2026-06-07 — Template deps: app packages baked into Containerfile

**Decision:** Keep `fastapi uvicorn httpx pydantic` baked into the Containerfile and `PYTHONPATH=/work` in `sandbox-run.sh` as template defaults. These are not validation-harness-only — they fix a universal bug: the non-root `agent` user (UID 1000) cannot `pip install --user` into system site-packages. Any FastAPI project in this template runs into the same failure.

**Alternatives considered:** (a) Remove baked deps, require every project to add its own via `requirements.txt` — every new project re-debugs the same user-site-packages issue. (b) Switch to root container user — defeats the isolation purpose. (c) Install via build agent at runtime — rejected because it is lost on container exit and is no longer used.

**Reason:** The four packages cover the most common FastAPI stack. The former runtime `pip install` fallback has been removed; the Containerfile guarantees the dependencies are present at build time. The `PYTHONPATH=/work` fix is similarly universal: without it, `from src.main import app` fails in the container regardless of project.

**Do not suggest:** Removing these deps from the Containerfile. Removing `PYTHONPATH=/work`. Both will cause the same failures for every new project and the fix will be re-discovered each time.

---

## D-16 — 2026-06-07 — Model pin: qwen/qwen3.6-35b-a3b (base) as default

**Decision:** Standardize on `qwen/qwen3.6-35b-a3b` (base model, 8-bit MLX, 37.75 GB) as the local build/test agent model. The `-ud-mlx` variant exists at 21.66 GB (4-bit) as a lower-memory fallback. The `opencode.json` config already points to the base model — this entry confirms it as the deliberate choice, not an accidental default.

**Alternatives considered:** (a) `qwen3.6-35b-a3b-ud-mlx` — 4-bit quantized, 21.66 GB, faster load but slightly lower quality. (b) `qwen/qwen3-coder-next` — 80B, 44.86 GB, too large for routine agent calls. (c) `[FRONTIER_MODEL]` — reserved for pm/architect only.

**Reason:** The base model seated 32K context at 35.16 GiB on M5 Max (128 GB unified memory), leaving ~90 GB for other workloads. The MLX variant loads in 21.66 GB but introduces a different serving path (unsorted, unproven for this project). The base model is the one the prompts were written and validated for. The two-tier cost model (frontier for planning, local for build/test) is preserved with a line at 35B, not 7B.

**Do not suggest:** Switching to `-ud-mlx` as the default; running build/test on frontier models permanently; dropping below 35B for writing agents.

---

## D-15 — 2026-06-07 — INV-2 gate: halt, not cleanup

**Decision:** Reverted the INV-2 gate handler in `scripts/orchestrate.sh` from cleanup+continue back to halt-and-flag (exit 1 with violation note in `tasks/CURRENT.md`). The prompt-hardening ("Write src/ only", "Write tests/ only") from the same commit was kept.

**Alternatives considered:** (a) Keep cleanup+continue — unblocks the run but silently swallows a boundary violation that should be visible. (b) Leave the gate as-is (soft-halt with inspection note but no exit) — same problem, different disguise.

**Reason:** A boundary violation (build wrote to `tests/` or test wrote to `src/`) is evidence that the model or instructions are wrong. That signal must stop the run and be recorded, not auto-swept. The halt is the enforcement; the gate (phase-gate.sh) is the detector. Cleaning up and continuing makes the violation invisible to the human keystone. The price of a halted run is the cost of INV-2 working correctly.

**Do not suggest:** Re-introducing cleanup+continue; treating a gate violation as a routine iteration failure rather than a process break.

---

## D-14 — 2026-06-07 — Context window ceiling measurement and fix

**Decision:** Measured the largest 35B agent payload (test agent: `.opencode/prompts/test.md` ~721B + orchestrator instruction ~166B + opencode system preamble ~8000B). Total estimated at ~3000 tokens. Raised LM Studio context length for `qwen/qwen3.6-35b-a3b` from the 8192 default to 32768 (32K) — four orders of magnitude over the measured need, with generous headroom for conversation history. The model natively supports 262144 (`max_position_embeddings` confirmed via HuggingFace config). Lever used: context bump, not prompt trim — the prompts themselves are small; the ceiling was LM Studio's default.

**Reason:** The 35B model's default context window in LM Studio (8192) was too small for the combined system preamble + agent prompt + instruction, causing context-length errors in prior runs. The model supports 256K native; 32K is a comfortable operating point that leaves GPU memory headroom (35.16 GiB used, 128 GiB available on M5 Max).

**Also changed:** `developer.separateReasoningContentInAPI` in `~/.lmstudio/settings.json` from `true` to `false`. When `true`, Qwen models that have reasoning enabled return `content: ''` with output in `reasoning_content` — opencode reads `content` only, so the model was unusable. Merging reasoning into `content` (even with the `<think>` block) keeps the model functional. To fully disable thinking (no reasoning tokens wasted), toggle the "Think" switch off in LM Studio UI for this model.

**Do not suggest:** Lowering context below 32K; switching to the `-ud-mlx` variant for context reasons only (the regular model seats 32K comfortably); trimming the agent prompts (they are not the bottleneck).

---

## D-13 — 2026-06-07 — Pipeline robustness fixes (container deps, PYTHONPATH, gate recovery)

**Decision:** Bake `fastapi uvicorn httpx pydantic` into Containerfile, add `PYTHONPATH=/work` to sandbox-run.sh, soften gate violations from hard-halt to cleanup+continue, and add `pip install` fallback before pytest.

**Alternatives considered:** Installing via `pip install --user` at runtime (fails — user site-packages not on Python search path), installing via build agent (lost on container exit), mounting host `site-packages` (fragile).

**Reason:** Non-root `agent` user (UID 1000) has no sudo and `pip install --user` drops to `~/.local/lib/python3.12/site-packages/` which Python does not search by default. The 35B model sometimes writes tests during build phase despite explicit prompts — cleanup+continue is more productive than halting. `pip install` before pytest ensures deps survive container rebuilds.

**Do not suggest:** Installing deps via the build agent (agent runs in disposable container, install lost on exit). Hard-halting on gate violations (35B model needs graceful recovery). Removing `PYTHONPATH` (required for `from src.main import app`).

---

## D-12 — 2026-06-06 — Local Model Tier: Qwen3.6-35B-A3B for Build/Test

**Decision:** Build and test agents default to `lms/qwen/qwen3.6-35b-a3b` (35B parameters, 3B active). The 7B `qwen3-coder-next` model produces malformed tool calls (omits required fields like `filePath` and `content` from the Write tool) and is removed from any file-writing role. PM and architect agents remain on `[FRONTIER_MODEL]` per the cost-tier design.

**Alternatives considered:**
- (a) Run all agents on frontier models — higher cost, negates local-tier savings
- (b) Wait for better 7B tool-calling support — uncertain timeline
- (c) Use Gemma-4-31B — not tested, but 35B Qwen writes files correctly

**Reason:** The 35B model is the smallest local model found that reliably constructs valid OpenCode tool calls. It writes files, installs dependencies, and passes gates. The two-tier cost model (frontier for planning, local for build/test) is preserved — the threshold is 35B, not 7B.

**Do not suggest:** Reverting build/test to the 7B model; running build/test on frontier models permanently.

---

## D-11 — 2026-06-06 — Agent Permission Model: No Catch-All Deny

**Decision:** The test agent's `edit` permission uses explicit `src/**": "deny"` and `tests/**": "allow"` with no `**": "deny"` catch-all. The catch-all overrode the specific allow because `**` matches `tests/` paths. Build agent keeps `tests/**": "deny"` with `**": "allow"` as its catch-all — reversed logic because build's allowed set (everything except tests) is too broad to enumerate.

**Alternatives considered:**
- (a) Keep `**": "deny"` and list every non-test directory explicitly — brittle, misses new directories
- (b) Use `--dangerously-skip-permissions` server-side — bypasses the entire permission model
- (c) Single agent with no role separation — violates INV-2

**Reason:** Explicit + allow with no deny catch-all is the simplest permission config that lets the test agent write files. OpenCode's permission engine applies matching deny rules regardless of specificity — a `**`: deny always catches `tests/` paths. Removing the catch-all fixes this at the config level.

**Do not suggest:** Re-adding `**": "deny"` to the test agent; adding `--dangerously-skip-permissions` as a permanent fix.

---

## D-10 — 2026-06-06 — macOS Compatibility Fixes for Sandbox Scripts

**Decision:** `scripts/sandbox-run.sh` and `scripts/orchestrate.sh` use `pwd -P` instead of `pwd` to resolve macOS `/tmp` → `/private/tmp` symlink for Podman bind-mount path matching. `sandbox-run.sh` uses Podman's built-in `--timeout` flag instead of external `timeout(1)` (which does not exist on macOS). `orchestrate.sh` detects `gtimeout` (macOS, from `brew install coreutils`) vs `timeout` (Linux) for its script-level agent timeout.

**Alternatives considered:**
- (a) Install coreutils on macOS and alias `timeout` — requires every macOS dev to opt in
- (b) Skip timeout entirely on macOS — agents hang indefinitely
- (c) Use Podman's `--timeout` only (already present) and skip the script-level wrapper — the wrapper is needed for the non-sandbox path and as a belt-and-suspenders guard

**Reason:** macOS is the primary development platform (verified by `uname`). The `/tmp` symlink (`/tmp` → `/private/tmp`) causes Podman bind-mount failures because the container resolves the physical path differently than the host. External `timeout(1)` is a Linux-only command. Podman's `--timeout` flag works on both platforms and replaces it. The `gtimeout`/`timeout` detection on the orchestrator's non-sandbox path follows the same pattern as the project's other platform-detection logic.

**Do not suggest:** Removing macOS support; switching to a Linux-only requirement; wrapping `timeout` in a shell function that fails silently.

---

## D-09 — 2026-06-06 — Sandbox Wiring in Orchestrator

**Decision:** `scripts/orchestrate.sh` routes agent calls and pytest through `scripts/sandbox-run.sh` when the `SANDBOX=1` environment variable is set. The sandbox path wraps each agent call with `timeout "${AGENT_TIMEOUT}"` (the container runs Debian where `timeout` is available from coreutils). The non-sandbox path uses `$TIMEOUT_CMD "${AGENT_TIMEOUT}"` (`gtimeout` on macOS, `timeout` on Linux). `SANDBOX_LLM_HOST` is read from the environment; both `orchestrate.sh` and `sandbox-run.sh` default it to `host.containers.internal` independently. When the orchestrator drives the run, its exported value is inherited by the container launcher; run standalone, `sandbox-run.sh` supplies its own default. The orchestrator does not hard-code the address — it reads the variable set upstream.

**Alternatives considered:**
- (a) Always run inside the sandbox, no fallback — breaks for developers without Podman
- (b) Hard-code `host.containers.internal` directly in `orchestrate.sh` — duplicates the address assumption that step 0 is supposed to prove
- (c) No sandbox path — forfeits container isolation

**Reason:** The `SANDBOX=1` env var is a single indirection point. Defaulting to `SANDBOX=0` preserves the existing non-sandbox workflow for development. The sandbox path delegates entirely to `sandbox-run.sh`, which is the single script that manages Podman flags, volume mounts, and the LLM host address. The orchestrator only knows `host.containers.internal` via the env var chain, not as a literal.

**Do not suggest:** Hard-coding `host.containers.internal` in `orchestrate.sh`; removing the `SANDBOX=0` fallback; adding a second sandboxing mechanism.

> **2026-06-09 correction:** The "SANDBOX=0 fallback" and "always run inside the sandbox" alternatives were revisited for AC9 compliance. The sandbox is now mandatory (no fallback). This decision entry is historical context; the current behavior is documented in the 2026-06-09 entry above.

---

## D-07 — 2026-06-06 — Four-role PRD→Plan→Build→Test pipeline

**Decision:** Adopted a four-role pipeline (PM, Architect, Build, Test) with two non-negotiable invariants: INV-1 (tests derive from the PRD, never from `src/` implementation) and INV-2 (Build never edits `tests/`; Test never edits `src/`). The PRD in `tasks/CURRENT.md` is the single oracle — the human's casual instruction is translated into structured acceptance criteria and flagged assumptions, then frozen on Approval. The Architect is also the orchestrator: it delegates build→test, runs `scripts/phase-gate.sh` after each phase, reads `.cache/test-report.json`, and routes failures per Rule 2/7 (build bug→build, same failure twice→re-plan, plan fails twice→PM).

**Alternatives considered:** (a) Extend the existing single-agent loop with role instructions in CLAUDE.md; (b) use OpenCode agent permissions alone for INV-2 enforcement; (c) keep the flat loop and add no roles.

**Reason:** A single-agent loop conflates planning, writing, and testing in one context — the model's self-judgment replaces the test-report oracle (Rule 5 drift) and nothing prevents it from writing tests that confirm what `src/` does rather than what the spec says (INV-1 violation). Separate roles with frozen contracts force the verification gap that catches bugs. OpenCode's agent permissions (`permission.edit` globs) are non-transitive — a restricted agent can bypass limits via the Task tool (opencode issues #12566, #20549) — so INV-2 is enforced mechanically by `scripts/phase-gate.sh`, not by permissions alone. Doc guards catch intent; mechanical gates catch the result (documented pattern from the 2026-06-04 auto-load entry). Cost rationale: build/test use the local model (free, 80% of tasks); pm/architect use frontier for reasoning walls and spec work.

**Do not suggest:** Letting the test agent read `src/` implementation to author tests (INV-1). Enforcing INV-2 with agent permissions alone — the git gate is the binding layer. Merging the four roles back into a single agent — the whole point is the verification gap between them. Letting the build or test agent edit the PRD or architecture docs.

---

## D-06 — 2026-06-06 — Adopted EARS for acceptance criteria

**Decision:** Acceptance criteria in `tasks/CURRENT.md` are now written in EARS notation (THE SYSTEM SHALL / WHEN...SHALL / WHILE...SHALL / IF...THEN SHALL / WHERE...SHALL). Each criterion is a single observable clause that maps one-to-one to a test case. The PM prompt enforces this at PRD time; the test prompt reinforces the mapping at test time. Template examples in CURRENT.md demonstrate all five forms plus an HTML-comment reference guide.

**Reason:** EARS forces each requirement into a single testable clause, giving the test agent an unambiguous oracle and tightening INV-1 enforcement. Vague prose criteria ("handles errors gracefully", "works correctly") were the weak point — the tester had to interpret intent, which reintroduces the ambiguity the pipeline was designed to eliminate. A one-clause-to-one-test mapping makes the test agent's job mechanical and removes the interpretation gap.

**Do not suggest:** Reverting to free-form prose criteria, or forcing all five EARS forms when a single SHALL clause suffices (avoid ceremony — see the repo's anti-over-engineering history, BLUEPRINT.md and DECISIONS.md prune entries).

---

## D-05 — 2026-06-06 — Code-driven orchestration loop

**Decision:** Moved loop control out of `architect.md` (where an LLM must remember to run the gate, read the test report, count strikes, and route) and into `scripts/orchestrate.sh`. The orchestrator is a shell script that drives the build→test loop deterministically: it starts a headless `opencode serve`, calls each agent via `opencode run --attach --agent <name>`, runs `scripts/phase-gate.sh` after each phase, parses the JSON test report via `python3 -c`, computes a `sha1(sorted(failing_node_ids))` signature for two-strike detection, and escalates to re-plan on identical failure signatures. The architect prompt shrinks to "produce/refresh the plan only."

**Reason:** Loop control in an LLM prompt is a doc-guard — the architect could forget to run the gate, mis-count strikes, or skip escalation. Moving it to a script makes the gate invocation, the two-strike counter, and the halt deterministic — each is a line of shell code, not a remembered instruction. Additionally, each scoped `opencode run` sidesteps the non-transitive-permission bug (each agent runs in its own invocation with its own permissions) and prevents context bloat over long loops. The script wraps each agent call in a `run_agent` function that is the single indirection point for future sandbox adoption.

**Do not suggest:** Putting orchestration logic back into `architect.md`, or auto-approving the PRD (the orchestrator refuses to run unless `Status: Approved`). Adding a queue, daemon, web UI, or multi-feature scheduling — one approved PRD, one run. Replacing the shell script with an orchestration framework (adopt OpenHands later if needed — note it in DECISIONS, don't pre-build for it).

**Server details (for posterity, empirically verified on OpenCode 1.15.13):**
- `opencode serve --port <n>` starts a headless server; default port is 0 (random), use `--port` explicitly.
- `opencode run --attach <url> --agent <name> <prompt>` calls a specific agent on the running server.
- Server is killed on script exit via `trap cleanup EXIT`.

---

## D-04 — 2026-06-06 — Demoted BLUEPRINT.md line-count gate to heuristic

**Decision:** Removed the failing `wc -l BLUEPRINT.md <= 450` check from CI and the correction log's hard-target language. The 450 number was self-imposed by the model during a pruning session, never a human requirement. Line count is a proxy that does not measure the real goal (no redundant/ambiguous content). Enforcement is replaced with a heuristic note at the bottom of BLUEPRINT.md.

**Documentation-only:** This decision documents a CI gate change; it does not change the API or build plan.

**Reason:** Enforcing a specific line count as a CI failure pressures edits to delete real content — including safety rules — to stay green. A mechanical gate is right for binary invariants (INV-2, placeholder completeness), wrong for a judgment call like doc leanness. The anti-bloat principle is genuine (BLUEPRINT is the LLM's entry point; redundancy is token cost and ambiguity risk), but enforcement should be human review and cross-reference discipline, not a numeric gate.

**Do not suggest:** Re-adding a failing line-count check, or compressing rules to hit a number. The "do not re-add pruned sections" guards in DECISIONS.md and human review are the correct mechanisms — they target redundancy directly.

---

## D-03 — 2026-06-04 — Removed CLAUDE.md mirror guard (decoupling template from project)

**Decision:** Remove the one-line "Do not re-add sections dropped from BLUEPRINT.md in the 2026-06-04 prune" guard from `CLAUDE.md`'s "What NOT To Do" → Operating guardrails. The rule still lives in `DECISIONS.md` → "Pruned BLUEPRINT.md" entry.

**Documentation-only:** This decision documents a doc decoupling action; it does not change the API or build plan.

**Reason:** CLAUDE.md is a template — `my-project` is still a placeholder. Baking a project-specific date ("2026-06-04 prune") into a template file makes the rule meaningless for any future project created from this template. The visibility argument was real but the template-vs-project boundary was muddied. The principle (don't re-add dropped sections) stays binding via DECISIONS.md's "Do not suggest" line and the correction log capture.

**Do not suggest:** Re-adding the mirror guard. Cross-reference, don't copy.

---

## D-02 — 2026-06-04 — Auto-load assumption corrected; CLAUDE.md / opencode.json fixes

**Decision:** (a) Rewrite `CLAUDE.md`'s intro to accurately describe its load behavior — file is *fetchable via tools*, not pre-loaded; the LLM is *expected* to read it. (b) Fix the project's `opencode.json` schema (OpenCode 1.15.13 rejects the old `providers` / top-level `models` form with "Unrecognized keys"). The original commit also added a "do not re-add dropped BLUEPRINT.md sections" mirror guard to `CLAUDE.md`; that mirror was later removed (see entry below) for template-hygiene reasons.

**Documentation-only:** This decision documents a measurement and fix to doc guards and config; it does not change the API or build plan.

**Alternatives considered:** (a) Document the asymmetry but not fix it; (b) add a hook in BLUEPRINT.md to force the LLM to read CLAUDE.md first; (c) leave the broken `opencode.json` and tell users to delete it.

**Reason:** The architectural premise that "guards in CLAUDE.md auto-fire every session" was unverified and partially false. Empirical test showed the model uses the `read` tool to fetch content (not pre-loaded) and can misparse which guard applies. The memory layer is best-effort, not enforced. For things that *must* hold, prefer mechanical gates (grep, `wc -l`, CI, git hooks) that fire without the LLM's cooperation. Doc guards are strong hints, not hard gates.

**Do not suggest:** Reverting `CLAUDE.md`'s intro to the "automatically read" claim, or reverting `opencode.json` to the old `providers` schema. Both are now verified-correct by empirical test.

**Verified by:**
- `opencode run --format json --dir /tmp/opencode-autoload-test "Read AGENTS.md..."` — event log showed `tool_use` with `read` tool; model fetched content but answered wrong
- `opencode --version` → `1.15.13` (matches the schema fix)
- `opencode run "What is 2+2?" --format default` from project dir → "Four." (schema fix loads cleanly under the installed version)

**Cross-cutting lesson (worth applying to all template projects):** Treat doc guards as advisory. For must-hold rules, build mechanical checks into scripts or CI:
- Placeholder completeness → grep (BLUEPRINT.md Step 7)
- File size budgets → `wc -l` in a pre-commit hook
- Schema validity → `opencode.json` parsed at session start
- Tests as ground truth → pytest in CI (BLUEPRINT.md Rule 5)
Doc guards catch the LLM's *intent*; mechanical gates catch the *result*. Both have a place. The test just proved the first is weaker than the design claimed.

---

## D-01 — 2026-06-04 — Pruned BLUEPRINT.md (557 → ~440 lines)

**Decision:** Apply the noise/redundancy findings from a parallel LLM audit; skip the lifecycle/strategy findings from a second LLM.
**Documentation-only:** This decision documents a doc-pruning action; it does not change the API or build plan.
**Alternatives considered:** (a) accept both LLMs' suggestions and add new rules; (b) leave the file as-is; (c) full rewrite.
**Reason:** BLUEPRINT.md is the LLM's entry point. Every redundant line is context-window cost and a chance for ambiguity to compound. Pruning is a guardrail against drift, not cosmetics. Adding more rules (the second LLM's "fortify" suggestions: Doc-Sync hard rule, TDD loop, REVIEW checkpoints, `/reset-context`) would partially undo the trim and add bloat.
**Do not suggest:** Re-adding the dropped sections. The "Document Map" alone is sufficient; the verbose "Document Roles Explained" was redundant. "Step 5 — Adapt the stack" is a pointer to Rule 3, not a restatement. Bootstrap cleanup, OpenCode Configuration, and Quick Reference Card are now minimal — keep them so.

**Trimmed (12 items, ~115 lines removed):**
- Dropped "Document Roles Explained" (duplicated Document Map)
- Collapsed Bootstrap Step 5 to a 1-line pointer to Rule 3
- Trimmed Maintenance Contract from 6 rows to 4 (dropped obvious triggers)
- Trimmed Files Never to Touch from 5 items to 3 (universal best-practice items removed)
- Shrunk Bootstrap Step 4 cleanup (24→6 lines)
- Trimmed Step 7 preamble (dropped "Hard Rule 5" restatement)
- Shrunk OpenCode Configuration section (28→3 lines + pointer to `opencode.json`)
- Trimmed anti-pattern "wrong provider name" to a one-liner
- Deleted Quick Reference Card (restated diagram + rules)
- Fixed phantom "Step 4.5" reference on line 490 → "Step 4"
- Reduced duplicate "lms not lmstudio" mentions from 3 to 1
- Reduced "AGENTS.md symlinks to CLAUDE.md" mentions from 5 to 3 (one in prose + 2 short callouts)

---
