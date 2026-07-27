# 2026-07-25 — turning a chat message into a reminder: what we considered

date: 2026-07-25
status: exploratory — no decision taken, nothing built, not in the backlog
seat: conductor (Claude Code, CEO session)

CEO question, verbatim in substance: convert any specific text entry into a
reminder — right now it's a web app, should it become a native app to create
reminders? Use Apple Reminders instead of building the feature from scratch?

Nothing was decided and nothing was built. Recording the reasoning because
the analysis is the durable part; if this comes back in a month the shape of
the answer shouldn't have to be re-derived.

## The premise that turned out to be wrong

The native-app question rested on "it's a web app, so it can't touch native
APIs." That's false for this architecture. The *frontend* is sandboxed in a
browser; the *backend* is a plain Python process running on the user's Mac
with their privileges. It can shell out to `osascript` today. The browser
never touches Reminders — it POSTs to our own localhost endpoint and the
backend does the native work.

Once that's clear, the native-rewrite question mostly dissolves: it would
mean rewriting a 151-test frozen-spec app to gain an integration already
reachable from where we are.

## Options weighed

**Build reminders from scratch — rejected.** It means building
*notifications*, and a reminder that only fires when a localhost tab happens
to be open is worse than none. Needs a background daemon, and creates a
second inbox competing with the one already on the user's phone, watch and
lock screen.

**Apple Reminders via the existing backend — the recommendation.** No
architecture change. iCloud sync, OS-level notification, and the "done"
checkbox lives where the user actually looks. Surface is one service module,
one endpoint, one button.

**Native rewrite (SwiftUI/Tauri/Electron) — rejected.** Buys EventKit
directly and a stable TCC identity, at the cost of the frozen-test oracle
that is the entire value of the pipeline here. Would be justified only for
*global* capture (hotkey, menu bar, share sheet) — a different product, and
the right vehicle for that is a small Swift menubar helper (the user has
already shipped one, trackpad-volume), not a rewrite of testchat.

**Mechanism within the recommendation:** `osascript` is the fast default;
PyObjC/EventKit is the escalation. EventKit is the "proper" API but a bare
python process has no `Info.plist`, so `NSRemindersUsageDescription` is
absent and the permission request can fail or misattribute. `shortcuts run`
is a robust third option (TCC handled by Shortcuts.app) at the cost of
user-side setup. Speed-first: start with osascript, escalate on specific
signals (date bugs, TCC instability, latency).

## The interaction that made it worth doing

Click ⏰ in the existing bubble chrome → modal opens *immediately*, prefilled
with the first ~60 chars as title, cursor in the field, Enter ships it. In
parallel, the local LLM extracts `{title, notes, due}` from the prose and
fills in a suggestion when it lands (~1-2s), without clobbering typed input.
Chat text is prose ("you should renew the domain before the 3rd"); reminders
want a short imperative plus a date. There's an LLM sitting right there — but
the fast path never blocks on it.

## Gotchas identified before writing any code

- **Never interpolate message text into an AppleScript string.** Chat
  messages contain quotes and backslashes. This is the same class as the
  `bash -c` token interpolation that was a *blocker* in the blueprint
  pre-publication review (`a9ff976`). Fix is the same: `osascript - "$text"`
  with `on run argv`, text as an argument, never concatenated into the body.
- **Pass date components, never a formatted string.** AppleScript date
  parsing is locale-dependent and silently produces wrong dates. Set
  `year`/`month`/`day`/`hours` numerically on `current date` — and set `day`
  to 1 first or month-end overflows (February 31).
- **TCC grant attaches to the responsible process**, which for uvicorn is the
  launching terminal. Different parent, possible re-prompt. Already bitten by
  this exact semantics on trackpad-volume ("posting process must hold the
  grant").
- **Cannot work from inside the Lima VM** — no macOS APIs there. The app must
  run on the host.
- **The frozen suite can't reach Reminders** (podman, `--network none`, no
  macOS), so the osascript call must sit behind a mockable service seam from
  day one — same shape as `src/services/llm.py`.
- **Write-only, no status sync.** Store the returned reminder id, render a
  "View in Reminders" link, never poll completion. A second status-staleness
  problem is already deferred (glyph-authority); don't buy another.

## The cost nobody asks about

M28 was a feature of almost identical shape — one UI affordance plus a modal
— and took four spec recuts and 11 post-`[success]` live-fixes, because
interaction quality leaks past the frozen oracle. If this is ever built, the
interaction ACs (cancel reverts, unavailable-path messaging, empty-text
disabled) belong in the spec up front, not discovered after success. That's
what blueprint D-82 exists for.
