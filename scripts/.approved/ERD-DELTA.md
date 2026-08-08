# ERD-DELTA — spec v86

The current milestone's slice of the spec. THIS FILE IS THE D-107 ERD-DELTA
referred to by the EM prompt: AC-48's recovered stop-mid-stream criterion is
re-entered into the standing PRD with its S5 "such that" post-condition
clause.

## Changed acceptance criteria

**AC-48 (recovered + re-cut):** the M9/M10 "Stop" behavior was one of the 23
ACs with no surviving PRD text (2026-07-25 lint) and was never checked for a
post-condition. Text recovered verbatim from refreeze v20 (`51149c1`) and
re-cut per the 2026-08-08 AC-48 audit verdict: added "such that the stream
ends and no further tokens arrive" as the S5 post-condition clause naming an
observable check.

## Superseded acceptance criteria

None — this is a PRD-text recovery, not a behavior change. The frozen test
(`test_stop_button_keeps_partial_reply`, M10 ratify) already pins the
observable pair (partial reply retained, "Send" restored, control re-enabled).

## Changed files

None — `contracts.changed_files` stays empty: PRD text only, no product code.

## Test-to-file mapping

Unchanged — the v84 mapping remains frozen data in `contracts.test_mapping`.