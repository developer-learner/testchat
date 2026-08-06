# Phase 5 — S1–S8 guard design specs (2026-08-06)

Design decisions for the spec-tier guards, per
`2026-08-06-phase5-baseline-instrumentation.md` taxonomy. Written for the
parallel session's build: each guard states what it ACCEPTS, what it
REJECTS, where it triggers, and the mechanism. Where a correction-log rule
or D-number already sanctions the rule, it is cited — build to that, don't
re-litigate.

## S1 — Unimplementable spec (satisfiability)

- **Trigger:** refreeze time, on the staged delta (`scripts/.approved/incoming`).
- **Accept:** every contract in the staged `contracts.json` is satisfiable
  against the CURRENT tree inventory — reuse the D-79 audit's exact
  semantics (`validate-plan.py --spec-preflight`, `old={}` form: everything
  already registered/on disk passes; what remains must be buildable by the
  inventory).
- **Reject:** any contract with no path from the inventory → block refreeze
  with the audit output verbatim. This is what M28's v51/v52 should have
  caught (~75 min of model swaps + seat escalation against an impossible
  spec).
- **Mechanism:** wire the existing D-79 audit as a refreeze pre-gate, not a
  halt-time diagnostic. Sanctioned by the D-79 correction-log entry
  (2026-07-19: "the delta below belongs to the TPM").

## S2 — Stale ERD guidance (D-107)

- **Trigger:** refreeze time, behavioral freezes.
- **Accept:** freeze ships an `ERD-DELTA.md` with non-empty sections, every
  new AC and every changed file in `contracts.files` covered by a section,
  and no contradiction with the standing `ERD.md`. ERD-DELTA is authoritative
  to the EM prompt until retired.
- **Reject:** a behavioral freeze with no ERD-DELTA, empty sections, or an
  uncovered new AC/file → block with the missing-coverage list.
- **Mechanism:** D-107 already specifies this; enforce it as a refreeze gate
  with mechanical section checks (header parse + coverage diff). M32's cost
  (five spec versions for six UI lines) is the bar.

## S3 — Stale briefs vs oracle (retire-on-refresh)

- **Trigger:** every spec-version refresh (refreeze install).
- **Accept:** briefs are derived from (or re-validated against) the current
  frozen oracle.
- **Reject:** a plan brief that outlives the spec version that shaped it —
  orchestrate must refuse a brief whose recorded spec version != FROZEN_V.
  M33's T4 chased a stale v74 brief against the v77 oracle (~25 min + 4 coder
  calls for done work).
- **Mechanism:** brief files carry their source spec version (header field);
  `ensure_plan` treats a stale-version brief as absent and re-derives from
  the current oracle. D-107's retire-on-refresh names the rule; make it
  mechanical.

## S4 — Restaged identical tests (palimpsest)

- **Trigger:** refreeze time, on `changed_tests`.
- **Accept:** `changed_tests` entries are NEW or substantially changed tests.
- **Reject:** a delta whose `changed_tests` contains a test byte-identical
  to the currently frozen one → block, and require a standing-ERD
  consolidation refreeze instead of a spec-only delta (the M33 close-out
  re-ran three completed tasks off ~50 restaged byte-identical tests).
- **Mechanism:** hash-compare staged tests vs the frozen suite; identical
  content with no ERD-DELTA coverage → reject with the consolidation
  directive.

## S5 — ACs as mechanisms, not outcomes (M29 lint)

- **Trigger:** refreeze time, AC lint over the staged spec.
- **Accept:** every AC whose verb changes resource state
  (spawn/terminate/kill/unload/evict/delete/release/clear/cancel) carries a
  post-condition clause naming an observable check ("such that <probe>
  fails"); staged tests contradict no live, un-retired AC; the delta lists
  the ACs it supersedes.
- **Reject:** a state-changing AC without an observable post-condition;
  a staged test contradicting a live AC (M29's unload suite asserted
  `MagicMock.send_signal` — 5/8 process-lifecycle ACs failed while the lint
  was absent).
- **Mechanism:** mechanical grep lint (the correction-log entry 2026-07-25
  already specifies the greppable shape) + the superseded-AC diff.

## S6 — Spec-staging discipline

- **Trigger:** orchestrate pre-flight, every run.
- **Accept:** run with a clean `scripts/.approved/incoming` (no staged-but-
  uninstalled delta) and a clean tree.
- **Reject:** `incoming/` populated, or tree dirty, when orchestrate
  starts → fail-closed. M34's EM plan calls ran against a STAGED spec
  (predated the `[refreeze v79]` commit, ~5 h 42 m run measured from the
  wrong basis).
- **Mechanism:** pre-flight check for `incoming/` non-emptiness (it is
  already gitignored — the check must be explicit, not trust the ignore).

## S7 — ERD section size vs brief cap (Rule 8)

- **Trigger:** refreeze time, ERD section length check.
- **Accept:** every ERD section short enough that a brief derived from it
  fits the 2500-char cap (bound: 1200 chars/section).
- **Reject:** an over-long section → block with the section named; the TPM
  splits or trims it. (Archive 2026-08-03: a 266-char ERD section fed a
  2541-char brief > the 2500 cap — the ERD shape, not the brief, was the
  defect.)
- **Mechanism:** mechanical length check at refreeze; the brief cap itself
  (Rule 8) is unchanged.

## S8 — Sandbox privilege mismatch

- **Trigger:** sandbox build (Containerfile) + verification.
- **Accept:** the sandbox container runs unprivileged (non-root) and the
  suite passes both sandbox and host.
- **Reject:** a sandbox that needs root privileges its host counterpart
  doesn't have; a suite green only in the privileged container. M29's
  `psutil.net_connections()` passed 153/153 in the root container and failed
  5 tests unprivileged on the host.
- **Mechanism:** drop root in `sandbox-run.sh` (already backlogged — build
  it), and keep the host re-run rule as the acceptance backstop.

## Build notes for the parallel session

- Every guard is a REFREEZE-TIME gate except S3 (orchestrate) and S6
  (orchestrate pre-flight) — orchestrate stays mine; hand me the S3/S6
  requirement list and I wire the orchestrate side.
- Each guard fails with the artifact named and the fix directive verbatim —
  no silent DROP anywhere in spec-tier (EM-tier repairs stay as-is).
- Guard tests: fixture-driven, one accept + one reject case per guard,
  mirroring the existing refreeze selftest style.
- The frontier TPM chat (my lane) ratifies these semantics into
  `TPM-ROLE.md` content and the spec-artifact schema additions; the build
  around the chat proceeds from this doc regardless.
