# Test-suite AC traceability audit — is the suite bloated / hallucinated?

**Source:** CEO question (2026-08-04) — three parts: are we over-testing; does a
test exist only because an LLM hallucinated one once; are we testing code the
milestone didn't touch. Audit run from the TPM seat with full read authority.
**Status:** complete. No spec/test change made. This note is the why-trail; the
tree is authoritative.
**Anchor:** testchat HEAD `21739fc`, spec `VERSION 79`, tests read from the
working tree (`tasks/CURRENT.md` was dirty at audit time; no test/spec files
were). Every number below was re-derived against the tree and the load-bearing
ones hand-verified a second way.

---

## Headline

The suite is **not bloated** and its tests are **not hallucinated**. The real,
measured issues are smaller and different: **stale AC labels** (traceability
drift) and **4 current ACs with no test** (a small coverage gap — the opposite
of over-testing). The genuine cost lever is **test time, not test count**.

## Verified numbers

| Quantity | Value | How derived |
|---|---|---|
| Test functions | 193 | `grep 'def test_'` across `tests/` |
| ACs in **current** approved spec | 44 | `scripts/.approved/{PRD,ERD,ERD-DELTA}.md` |
| ACs **ever** defined (79 versions) | 153 | union over git history of the approved specs |
| Distinct ACs **cited by tests** | 109 | `grep 'AC-[0-9]+' tests/` |
| Cited but not in current spec | 69 | set difference |
| — of those, **historical** (real prior-version AC) | **69** | present in some past spec blob |
| — of those, **true orphan** (never in any spec) | **0** | — |
| Current ACs with **no test** | 4 | AC-116, AC-124, AC-149, AC-150 |

Method for the 69: an AC counts as *historical* if it appears in **any**
committed version of the approved spec files, *true orphan* only if it appears
in **no** version ever. Union computed in Python (subprocess git calls, no shell
word-splitting) — see `classify_acs.py` in the audit scratchpad.

Hand-verified sample (not just the script): every checked "orphan" resolves to a
real, explicitly-superseded requirement —
- **AC-25** — commit `156b115c` (2026-07-26): *"explicitly retired AC-25"*
- **AC-102 / AC-103** — *"AC-95 — replaced by AC-102 and AC-103"*
- **AC-105** — *"AC-6 — replaced by AC-105"*

So the spec keeps an explicit supersession trail; retired ids stay documented as
replaced.

## Answers to the three questions

1. **Over-testing?** No. Using the right denominator (44 live ACs, not the
   inflated count an early pass used), it's ~1.75 tests per live AC — layered
   depth (logic / API / UI), not padding.
2. **Hallucinated tests?** Empirically zero. All 109 cited ACs trace to a real
   spec version. No invented anchors. The actual defect is **stale citations**:
   some tests carry AC *labels* that point at superseded ids (e.g. a test citing
   AC-25 after it was retired and renumbered). The behavior each such test
   asserts is still live; only its label is out of date — traceability drift,
   not dead or fake tests.
3. **Testing untouched code?** While building: no — only the changed file's
   tests run. At sign-off: yes — the whole suite reruns once as the regression
   net (per the milestone-cadence discussion; the ~60 browser tests are ~85% of
   the ~5-min wall clock). By design.

## Actionable

- **Coverage gap (small):** 4 current ACs have no test — AC-116, AC-124,
  AC-149, AC-150. AC-116 confirmed by hand: defined at
  `scripts/.approved/PRD.md:51`, zero citing test files. Some may be
  intentionally non-behavioral; this is the list to check at the next re-cut.
- **Traceability drift (cosmetic→moderate):** tests citing superseded AC ids.
  No behavior at risk; a re-anchor pass would restore label↔spec truth. Low
  priority.
- **The real lever is speed — but NOT cheap parallelization (CORRECTED
  2026-08-04).** An earlier version of this note claimed the ~60 browser tests
  could be parallelized ~4min→~1.5min cheaply. That is WRONG: the tests share a
  `scope="session"` app server on fixed ports (`STUB_PORT=8971`/`APP_PORT=8972`)
  + a single `TESTCHAT_DATA` file, and the autouse `_fresh_snapshot` fixture
  DELETEs all threads before each test — so naive `pytest-xdist` collides on
  ports and corrupts shared storage. "Isolated per-context" is browser-context
  only, not server/port/storage. Real parallelization needs per-worker
  ports/server/storage isolation (a conftest rework), not a dependency add, so
  the ~5-min suite is a fixed floor until then. There is almost nothing safe to
  DELETE either — the only redundancy found (~5 model-wiring tests mirroring the
  service layer) still asserts a distinct HTTP status and was left intact.

## Operator-seat note (why this is corpus-worthy)

This audit's **first** pass over-reached in exactly the way the CEO was probing.
It (a) cited a "one-test-per-requirement principle that just landed today" that
**does not exist** anywhere in the repo, and (b) quoted a ~4.7× tests-per-AC
ratio built on a **wrong denominator** (~40–51 "requirements" instead of the 44
real ACs). Both were caught only by grounding against the tree. Two further
silent bugs surfaced during the grounded re-run — zsh not word-splitting an
unquoted path list (produced a false "0 ACs ever defined"), and a `\b` in a zsh
grep aborting the historical check — each of which, unnoticed, would have
produced a confidently-wrong finding (the second would have reported "0 tests
anchored" or "69 true orphans"). The learning for the pipeline: the **review
layer hallucinates too**, and the only defense that held was re-derivation from
the tree plus hand-verification of the load-bearing claim. This is direct
evidence for making the test→requirement link machine-checkable rather than
prose-anchored — an orphan/stale-label check would have been decidable in one
command instead of an audit.
