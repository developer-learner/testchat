# Handoff — app.js split (catalog.js + chrome.js), hand-build + ratify

Written 2026-07-27 at testchat `233f76b` / blueprint `52855c6`. Approved
approach from the CEO session that landed D-90..D-94; execution deferred to
a fresh session. Read `project-trail/2026-07-27-m31-process-breaks.md` and
the blueprint's `project-trail/2026-07-27-proportionality-addendum.md` for
the machinery this leans on.

## Sequencing (CEO-agreed)

This is item #2. Item #1 — one small feature through the pipeline as the
live proof of D-86..D-94 (draft persistence or AC-101) — comes first unless
the CEO says otherwise. Nothing here blocks on it technically; the ordering
is about not confounding the first live-fire of the new machinery with the
workload shape the pipeline is worst at.

## Why hand-build + ratify, NOT a pipeline coder milestone

1. A behavior-preserving refactor produces zero new red tests — INV-1/D-75
   have nothing to grip, and the brief degenerates to "move code, change
   nothing": the Rule 8 negative-constraint shape that damaged index.html
   in M16.
2. The extracted files (~270 and ~150 lines) are 2x and 1x D-60's 150-line
   cap for whole-file coder writes.
3. The frozen oracle observes DOM testids, not JS wiring. The correction
   log has three green-suite/visibly-broken incidents; two are static
   JS/CSS. A lift-and-shift wiring break is the least detectable failure
   class this suite has.
4. Precedent: the first split (markdown.js, threads.js) and the M31 files
   (current-chat.js, sidebar-resize.js) all landed as hand-builds, then
   were ratified. That is this project's demonstrated pattern for
   structural work (blueprint D-63).

The partition rule that picked these cuts: minimize expected files touched
per CEO ask (things that change together stay together), under D-64's
one-file-per-task bijection. NOT lines-per-file — D-60 caps new-file
writes, not standing edit-mode files.

## Current shape (at `233f76b` — re-derive before cutting; line numbers drift
and parallel sessions edit this tree; `git status` first)

```
app.js            959   <- the target
threads.js        510   leave (single concern)
style.css        1515   leave (no-edit in most deltas; CSS damage is
                         invisible to the oracle — see correction log)
markdown.js 161 / rain.js 167 / current-chat.js 111 / sidebar-resize.js 75
```

app.js concern map (function anchors as of this commit):

| Lines (~) | Concern | Destination |
|---|---|---|
| 1–33 | element grabs, TC/MD/Threads refs, web toggle | stays |
| 34–56 | THEMES, applyTheme, theme toggle | **chrome.js** |
| 57–126 | focus mode (fullscreenEl, exitZen, fsDiag, onFullscreenChange) | **chrome.js** |
| 127–171 | pollStatus | decide on read — status line is chrome-ish, but check whether it reads model/catalog state; if coupled, leave in app.js this pass |
| 172–232 | settings modal + generic overlay-backdrop dismissal | **chrome.js** (the overlay dismissal helper is generic across ALL modals incl. load/unload confirms — keep it accessible to catalog.js, e.g. leave the delegation in app.js or export it) |
| 233–292 | bubble helpers, autogrow, stop button | stays |
| 293–597 | chat form submit + SSE stream | stays — explicitly out of scope |
| 598–664 | hover actions, copyToClipboard, code-block copy | stays |
| 665–931 | fetchModels, populateModelOptions, refreshModels, select pre-change capture, eject + load/unload confirm wiring | **catalog.js** |
| 932–959 | initial load | stays; calls into both new modules |

## Idiom

Match the existing pattern exactly: IIFE + `window.<Namespace>` globals
(`TC`, `MD`, `Threads`, `MatrixRain`), no ES modules, `var`, script tags in
`index.html` in dependency order (new tags BEFORE app.js). D-59 corollary
still applies to hand edits: never write a literal think-tag string.

## Coupling traps (each has burned a session before)

- **AC-28 mid-chat model lock is PARKED, 4 frozen tests enforce it.** The
  selector-lock logic couples catalog state to thread/streaming state.
  Move it verbatim; do not "improve" it.
- **Load-cancel revert reads the PRE-change select value** captured on
  focus/mousedown (comment at ~line 842). Prior bug: reading the
  just-picked value made cancel a no-op. Preserve the capture timing.
- **Glyph status authority is an intentional non-fix** (CEO call, 5s
  staleness accepted). Don't sync glyphs from /status.
- **Matrix rain + phosphor titlebar** are theme side effects inside
  applyTheme — they ride to chrome.js with it.
- Literal `<think>` swallowing is an intentional non-fix. Port 8080, never
  8000 (see PORT MAP in memory/CLAUDE.md).

## Verification protocol (the oracle is necessary, never sufficient)

1. Full suite on the HOST, not just sandbox (root-vs-unprivileged lesson):
   `PYTHONPATH=. pytest` — expect 176/176 (or current count) green before
   AND after, unchanged.
2. Real browser at :8080, verify the specific claims (M16 lesson —
   Playwright-green ≠ looks right): model dropdown populates; load confirm
   + cancel (cancel reverts selection); unload/eject flow; mid-chat lock
   still locks; theme cycle through all 10 incl. matrix (rain starts and
   stops) and phosphor (titlebar toggles); focus mode enter/exit; settings
   modal open/close; overlay-click dismisses each modal.
3. `git status` before every commit — parallel sessions edit this tree.

## Ratify freeze (after the hand-build is verified)

TPM recut, small: inventory += `src/static/catalog.js`,
`src/static/chrome.js` (contracts.files + ERD inventory), erd_version bump.
Details that will bite if skipped:

- **smoke_checks for both new files are REQUIRED** — they map zero tests
  (browser tests map to the final-closure task, D-64), and the plan gate
  rejects a task with neither tests nor smoke_check. Quote-agnostic
  patterns only (D-88 will reject brittle quoting).
- **Audit the EXISTING app.js smoke_check** — if its grep targets code
  that moved out, acceptance fails post-split. Re-point or replace it.
- index.html gains the two script tags during the hand-build, so D-87's
  reachability preflight passes at freeze time.
- Expected pipeline behavior on the next run: subtree re-plan arms; scope
  = 2 new files, 0 re-emits, 0 map ids → ONE small EM subtree call for the
  two new tasks; both files exist on disk and are outside the delta's
  affected set → coder never invoked (inverted no-edit); acceptance +
  full suite run. The D-86 "delta scopes NOTHING" warning may print for
  the changed_files field — expected for a ratify; nothing is unbuilt.
- Refreeze may run on the host: D-90 gives real pytest collection and a
  red-check verdict there now. D-75 will report "no runnable test
  changes" — correct for a ratify.

Check whether this closes the backlog's "M13 — app.js module split (spec
backfill)" item (P2) — if the recut ERD documents the full current module
layout, mark it done in `tasks/BACKLOG.md`.

## Non-goals

chat-send/SSE extraction (fragile, changes co-occur with bubble rendering
— wait for an ask that forces it); style.css split; threads.js; anything
listed as an intentional non-fix; AC-28 in any form.

## Estimate

Hand-build + browser verify: 1–2 focused hours. Ratify freeze + run:
~10 min. Commits: extraction as one or two `ui:` live-fix commits (no
Co-Authored-By trailer), then the `[refreeze vN]` from the TPM relay.

---

## Shipped 2026-07-27 — hand-build (ad hoc, NOT via the pipeline)

Landed at `2579f07` on `main` as a single `ui:` commit. Explicitly
**not** a milestone: this did not go through `orchestrate.sh`, no
TPM spec, no EM plan, no coder invocation — a conductor-driven
lift-and-shift, per the rationale in "Why hand-build + ratify" above
(Rule 8 negative-constraint shape, D-60's 150-line cap on new-file
coder writes, the frozen oracle's blind spot on JS wiring). The
ratify freeze is the pipeline's touch on this work and is still
pending — that is the TPM recut that adds the two new files to the
ERD inventory + `contracts.files`.

**Files after the cut** (was `app.js` 959):

| File | Lines | Concern |
|---|---|---|
| `src/static/app.js` | 550 | chat surface: bubbles, SSE stream, stop, pollStatus, hover/copy/thinkToggle/newThreadBtn, Send-with-unloaded-model flow |
| `src/static/chrome.js` | 171 | themes (10 + rain/phosphor side effects), focus mode, settings modal, generic overlay backdrop dismissal, Escape handler |
| `src/static/catalog.js` | 304 | fetchModels + populateModelOptions + refreshModels, eject/unload confirm, select pre-change capture, change handler with AC-28 mid-chat lock coupling |
| `src/static/index.html` | +2 | chrome + catalog script tags before app.js |

Net +66 lines (three IIFE wrappers, one added comment about the
shared load-confirm modal, and the `window.App` / `window.Catalog`
publish blocks). No behavior changes intended.

**Decision points during execution:**

- `pollStatus` **stayed in app.js**, not moved to chrome. It reads
  `modelSelect.value` + option `dataset.loaded`, controls
  `sendBtn.disabled` and `ejectModelBtn.disabled`, and mutates
  `webToggle.disabled` from `/api/v1/status.web_configured` — coupled
  to both catalog and chat. Moving it would have created a three-way
  namespace tangle for zero benefit. Handoff said "if coupled, leave
  in app.js" — confirmed coupled.
- **Shared load-confirm modal.** app.js keeps the load-confirm modal
  element grabs because its own Send-with-unloaded-model flow drives
  the same modal, reassigning `loadCancelBtn.onclick` /
  `loadConfirmBtn.onclick`. Only one flow runs at a time; latest
  write wins, which is fine. Called out in a comment at the app.js
  element-grab block.
- **Cross-module contract.** app.js publishes
  `window.App = { appendBubble, pollStatus }`; catalog.js publishes
  `window.Catalog = { fetchModels, refreshModels }`; chrome.js is
  self-contained (returns `{}`). chrome.js and catalog.js reference
  `window.App.*` lazily inside handlers, so the app.js publish at
  the end of its IIFE lands before any handler fires.
- **Script tag order** in index.html: rain → markdown → threads →
  current-chat → sidebar-resize → **chrome → catalog** → app. chrome
  and catalog can safely `getElementById` at IIFE-init because every
  DOM element they reference is present in index.html at parse time.

**Verification that ran on the host (not sandbox):**

- `PYTHONPATH=. pytest`: 176/176 in 277.79s. Same count as before
  the cut, unchanged.
- Live app at `:8080` with real browser (in-app Browser pane):
  - Globals: `App`, `Chrome`, `Catalog`, `TC`, `Threads`, `MD`,
    `MatrixRain`, `CurrentChat` all present.
  - Themes: cycled all 10, correct icons, matrix canvas mounts on
    matrix, phosphor titlebar `display: flex` only on phosphor.
  - Settings modal: opens on toggle click, closes on cancel button /
    backdrop click / Escape.
  - Escape correctly fires the cancel button of load / unload /
    delete confirm modals (owned by app+catalog / catalog / threads
    respectively, all dismissed by the shared chrome handler).
  - Catalog change handler: picked an unloaded option, load-confirm
    modal opened with model id + RAM text, cancel reverted the
    selection to the pre-change value (AC-104 focus/mousedown
    capture timing preserved).
  - **AC-28 verified live**: set `TC.modelLoading = true`, picked a
    second unloaded option — modal stayed hidden and selection
    reverted immediately, matching the overlapping-load guard.
  - No console errors at any point.
- No live-fire load/unload/eject round-trip because no local LLM
  server was running this session — the catalog rendered its two
  script-model options (nemotron, deepseek-v4-flash, both unloaded)
  from `/api/v1/models/catalog`, which is enough to exercise the
  change handler and the AC-28 guard; the actual `/load` and
  `/unload` HTTP paths are unchanged from pre-split app.js.

**Follow-up for the ratify session (already in the commit message):**

The existing `scripts/.approved/contracts.json` smoke_check for
`src/static/app.js` greps for `ejectModelBtn` and `models/catalog`
— both moved to catalog.js. Next `orchestrate.sh` will go red on
that check until the TPM recut re-authors it and adds smoke_checks
for `chrome.js` and `catalog.js` (D-88 quote-agnostic patterns).
No frozen tests need to change — this is a spec-only refreeze
adding two files to the inventory and updating one smoke_check.

Sequencing note stands: the CEO's item #1 (one small feature through
the pipeline as live proof of D-86..D-94) is still the next thing;
the ratify freeze for this split rides afterward.
