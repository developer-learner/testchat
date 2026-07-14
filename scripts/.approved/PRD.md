PRD — testchat M17: Loadable-Memory Counter

Milestone

The status strip's RAM readout answers the wrong question. It shows a
used/total figure that matches neither Activity Monitor nor the decision
the CEO actually makes with it: "can I load another LLM without bringing
the machine down?" macOS has no single 'used RAM' truth — file cache is
reclaimable, and model weights are wired against a separate GPU limit — so
M17 adds the number that answers the real question: an estimate of how many
GB a NEW model load can safely claim, accounting for both reclaimable
system memory and the Apple Silicon GPU wired-memory cap.

Acceptance Criteria

- AC-60: WHEN /api/v1/status is requested, the payload SHALL include
  loadable_gb: a non-negative number, no greater than ram_total_gb,
  estimating how many GB a new model load can safely claim.
- AC-61: WHERE loadable capacity is computed, the estimate SHALL be the
  MINIMUM of (a) reclaimable system memory (free + speculative + purgeable
  + file-backed pages) and (b) remaining GPU wired-memory headroom (the
  iogpu wired limit, or 75% of total RAM when unset, minus pages already
  wired), less a 4 GB safety margin, floored at zero.
- AC-62: WHEN the status strip renders, it SHALL display the loadable
  estimate (e.g. "~58 GB loadable") alongside the existing RAM figures.
- Existing fields (ram_used_gb, ram_total_gb, nemotron_rss_gb,
  nemotron_loaded) remain unchanged — additive change only.

Out of Scope: changing the ram_used_gb formula, per-model breakdowns,
warnings/alerts, polling cadence changes.

CEO Demo Script

1. Open the app — status strip now reads like:
   "RAM 64/128 GB · ~52 GB loadable".
2. Sanity-check against reality: with the two qwens resident (~67 GB
   wired), the loadable figure should be roughly the GPU headroom — small
   enough to warn you off a 50 GB Nemotron load while they're resident.
3. Unload a qwen in LM Studio, wait a poll (~5s) — loadable rises by
   roughly that model's size.
4. The old used/total figure still shows; nothing else moved.
