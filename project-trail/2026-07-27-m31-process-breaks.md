# M31 arc — record of process breaks

**Trigger:** CEO asked for two features — the current chat's title in the header, and refresh opening the newest thread. Bundled into milestone M31 ("current-chat awareness"), 16 ACs (AC-111..AC-126), 15 new frozen tests.
**Duration:** 2026-07-25 → 2026-07-27.
**Outcome:** milestone never built through the pipeline; TPM role vacated after v64 (five refreeze cycles); milestone then hand-built directly on the tree in ~23 min per CEO direction.

Every claim below is anchored to project-trail files that were written live during the arc:
`2026-07-26-blueprint-findings.md`, `2026-07-26-m31-handoff.md`, `2026-07-27-m31-tpm-handoff.md`. Not derived from memory.

---

## Part 1 — the five pipeline halts (all TPM-authored, all mechanically detectable at freeze time)

| Ver | Role that failed | Defect | What the pipeline saw | Existing gate that would have caught it |
|---|---|---|---|---|
| **v60** | TPM (spec authoring) | First-pass M31 spec under-scoped the delta; combined with the correct inverted-no-edit default, every existing file became untouchable | Coder never invoked; acceptance only ran no-edit paths | none |
| **v61** | TPM (smoke_check authoring) | `grep -q '[data-active="true"]'` in a smoke_check; coder wrote `[data-active='true']` — identical CSS, different quote char | 4 coder strikes + 2 EM diagnosis calls (62s), escalation halt against a **correct** file | none |
| **v62** | TPM (inventory authoring) + gate design gap | Added `src/static/current-chat.css` to `contracts.files`. The only file that could `<link>` it (`index.html`) was outside the delta; `style.css` was `no_edit`. Physically unreachable | CEO caught it in a pre-run check; the pipeline would have produced correct dead code | D-78 satisfiability preflight covers routes/entry_points, not static-asset reachability |
| **v63** | TPM + `refreeze.sh` **bug** | Spec-only refreeze produced an empty delta (`changed_files: []`, `changed_tests: 0`, `changed_contract_ids: []`). With inverted no-edit, this locked the coder out of every existing file. Silent | Run reported normally | none. Root cause is `refreeze.sh` itself: L527 populates `changed_tests` from *presence in staging*, not content diff; L532 hardcodes `changed_files: []`; contract-id delta walks only entry_points/routes/schemas/errors — **never `ui`** |
| **v64** | TPM | Chose to reduce scope by compressing prose in one brief instead of splitting scope across a new file. T7 (`app.js`) brief hit 2697 chars vs 2500 plan-gate cap | 2 EM revision attempts (~10 min on mlx-serve 4-bit), then plan gate halt | none at freeze time. Cap is enforced only after each ~250–280s EM call |

**Common shape:** every halt was a spec defect I authored. EM validated its plan first-attempt at v63; coder output was correct in every completed task; no infrastructure failure. The pipeline's execution tiers were reliable. The specification tier was not.

---

## Part 2 — pipeline structural gaps this arc exposed

Not defects of any actor; missing guardrails that would defend future TPMs regardless of model class.

1. **No new-file-reachability preflight.** A new file in `contracts.files` with no existing referencing file — and whose only possible referencer is `no_edit` or outside the delta — is dead-on-arrival. Cheap to check (a grep over inventory). Documented as blueprint finding #3.
2. **No non-empty-delta gate on unbuilt milestone.** An empty `DELTA-vN.json` while the current milestone is unbuilt should refuse the freeze, per the same principle already applied to lost `.pipeline-state`: absence of state must read as *unknown*, never *nothing to do*. Documented as blueprint finding #2.
3. **No quote-agnostic lint on `smoke_checks`.** A shell grep for a source token must not be defeatable by a synonym punctuation. Documented as blueprint finding #5.
4. **No brief-size lint at spec time.** The plan-gate cap fires only after the EM call. A pre-freeze estimate would halt in seconds not minutes.
5. **`refreeze.sh` is itself the delta-source-of-truth and it silently ignores UI-only changes.** L394-416 contract-id walk never visits `ui`. This is a bug in the tool, not a policy gap.

---

## Part 3 — economics

From `2026-07-26-blueprint-findings.md` (Run A, mlx-serve 4-bit, `SWBP_RUN_BUDGET=3600`):

| Phase | Time | Share |
|---|---|---|
| EM plan call | 282s | **68%** |
| EM diagnosis calls (×2) | 62s | 15% |
| Acceptance runs (×7) | 42s | 10% |
| Coder call | 15s | 4% |
| Pre-flight/gates/commits | ~12s | 3% |
| **Halt** | **413s** | |

- One clean run ≈ 7 min; a halt on the second EM revision ≈ 10 min.
- Five refreeze cycles cost >30 min of EM time alone, before any human work between them.
- The 68% cost is because the EM re-emits the full inventory every run (D-64 bijection), not a delta. The single largest lever if only one thing changes.

---

## Part 4 — what the hand-build revealed about the frozen suite

Immediately after the hand-build passed 170/170, CEO exercised the app and surfaced six real bugs, four of which were latent in production for weeks-to-months. **None had frozen-test coverage.** The oracle passing did not mean the app was correct.

| # | Bug | Where the escape happened |
|---|---|---|
| 1 | Copy-bubble pasted raw `<think>` tags on history-loaded messages | Live-stream path stripped in `renderReply`; reload path in `renderThreadMessages` did not. Zero tests exercise the copy button |
| 2 | Titles had `...` baked into the stored string at 30 chars (widening sidebar could never reveal more; header + tooltip inherited the stump) | Frozen test asserts only a prefix of the first message, so 30-char truncation was invisible to it |
| 3 | Sidebar not draggable | Feature gap; no test covers layout affordances |
| 4 | Model dropdown dead end — a pre-selected unloaded model could not be triggered to load (re-pick fires no `change`), and Send returned bare HTTP 422 with no handler | `test_model_option_labels_never_carry_checkmark` mocks the catalog with a loaded model; the unloaded-state path is never exercised |
| 5 | `createThread` copied the sticky dropdown value (always unloaded deepseek across restarts) into every new chat | No test |
| 6 | Data pollution: 19 of 46 stored titles had `...` baked in, thread 70's stored user text was `<think>We </think><think>need to in</think>…` from bug #1 escaping into a paste | No test / not oracle territory |

Bugs 1–5 are code defects the frozen suite considered green. Bug 6 is the downstream data damage.

---

## Part 5 — untested code shipped during the hand-build

The four items I built after CEO's "finish the job" have no frozen test at all:

| Item | Files | Test coverage |
|---|---|---|
| history-load copy strip | `src/static/threads.js:107-125` | none |
| sidebar-resize module | `src/static/sidebar-resize.{js,css}` (new) | none |
| title cap 120 (no baked ellipsis) | `src/static/threads.js:352-370` | none — pinned prefix only |
| dropdown auto-pick + placeholder + Send-time load flow | `src/static/app.js`, `current-chat.css` | none |

INV-1 forbids agents from authoring tests. I can flag the gap; only TPM can close it.

---

## Part 6 — direct observations on the role model

1. **The pipeline's execution tiers held up.** EM plan first-try on v63. Coder output correct in every task it ran. mlx-serve 4-bit outperformed the D-72 record. The tiers below spec-authoring were not the failure surface in this arc.
2. **Spec-authoring was every failure.** Five for five. Verification discipline, not reasoning difficulty — every defect was mechanically detectable before freeze using tools already in the repo (`validate-plan.py`, one `grep`, inspecting `DELTA-vN.json`). I did not run them.
3. **The pipeline had no mechanical defense against 4 of the 5 defects.** Rule from CLAUDE.md itself: "a rule that cannot be enforced mechanically is a suggestion." The blueprint's own findings from this arc are gate-shaped.
4. **Frozen-suite green ≠ acceptance.** Six real bugs, some ancient, lived under a green oracle. Interaction quality, error paths, feature gaps, layout affordances, data-migration correctness — all uncovered surfaces per the pattern. Blueprint D-82 was already noted as the mechanism for this from M28; it did not carry into M31 authoring.
5. **The hand-build worked but broke INV-1 in effect.** I built 4 features with no tests. The suite is now behind the code, and the pipeline can no longer trust its own oracle for those areas. Not a defense — just naming it as another break to record.

---

## What is NOT in this log

- Recommendations, next steps, or a proposed process fix. CEO explicitly paused feature work to figure out why the roles are breaking; conclusions are theirs, not mine.
- The bugs I fixed during hand-build. The fixes are in the tree, unrelated to the process question.
- v65 direction. Handoff at `2026-07-27-m31-tpm-handoff.md` covers it; kept out of here to keep this a break-log, not a plan.
