# Handoff → blueprint session: two un-gated defect classes from testchat M31

**For:** the session working in `~/dev/sw-dev-blueprint` (author of D-86 `559b6d2` and D-87 `7b229ba`).
**From:** the testchat session. **Date:** 2026-07-27.
**Status when written:** blueprint main at `7b229ba`, both gate commits unpushed. testchat synced to `7b229baa08dc` at child commit `7d20cca` — template flow is healthy; whatever you land next syncs normally.

D-86/D-87 closed three of the five M31 halt classes (v60/v62/v63). These are the remaining two. Evidence lives in testchat `project-trail/2026-07-26-blueprint-findings.md` (finding 5) and `project-trail/2026-07-27-m31-tpm-handoff.md` (v64 row); reproductions below are self-contained.

---

## Class 1 — quote-brittle smoke_checks (M31 v61; also finding 5)

**Reproduction.** Frozen `contracts.json` carried:

```
grep -q '\[data-active="true"\]' src/static/current-chat.css
```

The coder wrote `[data-active='true']` — byte-different, semantically identical CSS. Cost: 4 coder strikes + 2 EM diagnosis calls (62s) + an escalation halt, all against a file that satisfied the spec. The failure mode is a **spec-authored oracle rejecting a correct implementation**, which the ladder cannot recover from below the TPM rung.

**Gate shape (freeze-time, deterministic).** In `refreeze.sh`'s staging validation (or `validate-plan.py --spec-preflight`, which already reads contracts): for each `smoke_checks` entry whose command greps a source token, flag a pattern containing a literal `'` or `"` **inside the matched text** unless it uses a character class (`['\"]`). Advisory is enough — name the entry and print the quote-agnostic rewrite:

```
grep -qE "\[data-active=['\"]true['\"]\]"
```

A stricter variant (reject, not warn) is defensible since the TPM can always restage; your call. Selftest: pin the v61 pair — brittle pattern flagged, `['\"]` form passes.

**Not proposed:** trying to prove the grep matches the eventual implementation (unknowable at freeze). Only the *robustness class* of the pattern is checkable, and that is exactly the part that failed.

---

## Class 2 — brief-size overflow discovered only after the EM call (M31 v64)

**Reproduction.** v64's ERD concentrated 12 behavioral items on `src/static/app.js`. The EM's brief for that task came out 2697 chars against `MAX_BRIEF_CHARS = 2500` (`validate-plan.py:60`). The gate fired **after** two EM plan calls (~250–280s each on the 4-bit seat, 68% of run wall clock) — ~10 minutes to learn what the ERD already implied at freeze time. Retry could never succeed: the overshoot was structural (spec mass per file), not model variance.

**Why this can't be a plan-gate fix.** Briefs don't exist at freeze; only the ERD does. The checkable freeze-time signal is **spec mass per inventory file**: the size of each file's behavioral-specification section in the staged ERD (and/or its AC count). v64's app.js section was far past what transcribes into 2500 chars; the correct fix (split into a new file — which the CEO's v65 direction and the eventual hand-build both confirmed) was visible in that number alone.

**Gate shape (freeze-time, advisory).** In the spec preflight: parse the staged ERD's per-file sections (the per-file structure already exists — v64's repair edited exactly those sections), and warn when any single file's section exceeds a threshold (~2,000 chars of behavioral spec, tune against history: v63's app.js section transcribed to a passing brief; v64's did not). Message should say the remedy, which D-60 already legislates: *one concern per brief — split the feature into its own file*. Advisory, never blocking: the correlation between ERD mass and brief size is strong but heuristic, and the EM's plan gate remains the hard backstop.

**Cheap complement:** the plan-gate failure message already says "split the task or tighten the brief" — consider having orchestrate's halt text also name the file's ERD section size, so a future TPM sees "the spec is oversized," not "the EM wrote long."

---

## Ordering note

Class 1 is an hour including selftests; class 2 needs a small design pass on the ERD-section parser. Both are TPM-protecting gates in the same spirit as D-86/D-87: the M31 postmortem's conclusion was that every halt was mechanically detectable at freeze time, and these are the last two without a mechanical detector.
