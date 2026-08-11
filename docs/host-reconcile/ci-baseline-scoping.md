# HOST-RECONCILE: CI-baseline scoping (`check_ci_health`)

**Status:** DRAFT — host-verify only. Authored in a hermetic cloud container
with **no `gh`, no `origin` CI, no remote runs**, so the behavior below is
**not verified here** and must never be reported green until a host with real
CI applies and exercises it. This file is intentionally OUT of the main commit
and OUT of `scripts/.manifest-template` (it changes no manifest-pinned bytes).

Relates to: audit 2026-08-11 item 2, third check — "existing red CI
hard-blocks runs unless manually overridden. Investigate the mechanism and
scope it (baseline only the pre-existing red, gate the delta's new surface)."

---

## Mechanism today (D-85)

`scripts/orchestrate.sh::check_ci_health` (≈ lines 389–459) makes one
`gh run list --branch <branch>` call, keeps the newest run per workflow, and
computes `red` = the set of workflows whose newest run `completed` with
`conclusion == failure`. Any non-empty `red` is a hard `die` that stops the
whole run. The only relief is the blunt env override
`SWBP_SKIP_CI_CHECK=1`, which disables the check entirely — so a single
pre-existing red workflow (unrelated to the current milestone) forces the
operator to run the milestone with **no** CI gate at all, or not at all.

That is the whole-project blocking the audit flags: the gate cannot tell a
red the current delta *introduced* from a red that was already there.

## Scoping goal

Block only on **newly-red** workflows — reds this milestone's surface is
responsible for. A workflow that was already red before the milestone started
is *baselined*: reported, not blocking. A baselined workflow that turns green
again is dropped from the baseline, so a later regression on it blocks again
(auto-heal — a baseline is a snapshot of accepted pre-existing red, never a
permanent mute).

## Proposed change (orchestrate.sh — OUTSIDE the lane's run_tests fence)

> This edit lands in `check_ci_health`, which is **not** in this lane's scope
> fence (that fence is the `run_tests` type-gate region only). It therefore
> stays here as a draft for the host lane to apply, so the main commit's
> `orchestrate.sh` hash reflects only the mypy-scope change.

Durable baseline file (survives the `[success]` teardown that wipes
`.pipeline-state/` — D-108/D-126 lesson: derived data that must persist across
milestones lives OUTSIDE the blast radius):

    .measurement/ci-red-baseline      # one workflowName per line

Record step (run once to snapshot known pre-existing red, e.g. after
inspecting CI): `SWBP_CI_RECORD_BASELINE=1 scripts/orchestrate.sh` writes the
current `red` set to the baseline file and proceeds.

Verdict handling in the `RED)` branch becomes:

```sh
    RED)
      base_file=".measurement/ci-red-baseline"
      mkdir -p .measurement
      # newest-green workflows auto-heal out of the baseline
      if [ -f "$base_file" ]; then
        green_now=$(printf '%s' "$runs_json" | python3 -c '
import json,sys
runs=json.load(sys.stdin); latest={}
for r in runs: latest.setdefault(r.get("workflowName") or "?", r)
print("\n".join(sorted(n for n,r in latest.items()
      if r.get("status")=="completed" and r.get("conclusion")=="success")))')
        if [ -n "$green_now" ]; then
          grep -vxF -f <(printf '%s\n' "$green_now") "$base_file" \
            > "$base_file.tmp" 2>/dev/null && mv "$base_file.tmp" "$base_file" || true
        fi
      fi
      if [ "${SWBP_CI_RECORD_BASELINE:-0}" = "1" ]; then
        printf '%s\n' "${detail//, /$'\n'}" | sort -u > "$base_file"
        echo "  CI health: recorded ${detail} as the pre-existing red baseline — proceeding"
        return 0
      fi
      # split current red into carried (baselined) vs new (this delta's)
      new_red=$(comm -23 \
        <(printf '%s\n' "${detail//, /$'\n'}" | sort -u) \
        <(sort -u "$base_file" 2>/dev/null) | paste -sd, -)
      if [ -z "$new_red" ]; then
        echo "  CI health: red only on baselined pre-existing workflow(s) ($detail) — not blocking; the delta's surface is green"
        return 0
      fi
      die "CI is RED on NEW workflow(s) this run is responsible for: $new_red
  (baselined pre-existing red, if any, was ignored: see .measurement/ci-red-baseline)
  ... <existing guidance, incl. SWBP_SKIP_CI_CHECK=1 escape hatch> ..." ;;
```

`SWBP_SKIP_CI_CHECK=1` is retained unchanged as the total-bypass escape hatch.

## Open decisions for the host lane

1. **Baseline capture timing.** Explicit `SWBP_CI_RECORD_BASELINE=1` (above) is
   the least-surprising: the operator snapshots known pre-existing red once,
   deliberately. An automatic "capture red at milestone start" is possible but
   risks silently baselining a red the delta actually caused if the first run
   is late. Recommend the explicit form.
2. **`ci.yml`?** No `ci.yml` change is required for this design — the scoping
   is entirely in `check_ci_health`. If the host lane instead prefers to gate
   per-workflow by changed paths (workflow `paths:` filters), THAT is a
   `ci.yml` edit and per the audit must be its **own** commit titled
   `HOST-RECONCILE: ci.yml`, excluded from the main commit (ci.yml is
   project-owned, not template-owned, and not in `.manifest-template`).
3. **Verification.** Must be exercised against a real branch with (a) a
   pre-existing red workflow → baseline → proceed; (b) a newly-red workflow →
   die; (c) a baselined workflow going green → dropped, then re-red → die.
   None of this is reproducible in the hermetic container (no `gh`).
