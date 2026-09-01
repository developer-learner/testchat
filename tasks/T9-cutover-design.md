# T9 — Vortex cutover: accepted design target

**CEO-approved 2026-09-01.** Decision: **keep both** — Vortex is the primary
model source; the legacy local path (LM Studio + script models) is **retained
as a fallback**, not removed. Prototype the CEO signed off on:
https://claude.ai/code/artifact/c51af3cc-6905-4ecc-bf17-35e967d6def0

This note is the design target for the T9 milestone. It is NOT the frozen spec —
the TPM seat authors the PRD/ERD/tests (freeze-first) when the milestone runs.
The v114 recut already shipped the router seams (`is_router_configured`,
`router_chat_endpoint`, `router_models`, `is_router_model`, `VORTEX_URL`); T9 is
the cutover that makes Vortex primary and the picker ready-only.

## Accepted behaviour (acceptance-criteria seeds)

1. **Ready-only picker.** The model picker lists ONLY models that are loaded and
   ready to chat. It must NOT list the full catalog of unloaded models.
2. **Two labelled groups.** "Vortex · shared · primary" (models from the
   universal `/v1/models` surface) on top; "Local · this machine · fallback"
   (ready LM Studio / script models) underneath.
3. **Manage link.** A "Manage models in Vortex ↗" action at the bottom of the
   Vortex group opens the Vortex dashboard (`http://127.0.0.1:9000/`) in a new
   tab. Loading, unloading, the full catalog and RAM live in Vortex — never in
   Testchat.
4. **Fallback / offline.** When Vortex is unreachable: the Vortex group and the
   manage link are disabled, ready local models remain selectable, and the
   active-model status reads "via local". Chat keeps working on the fallback.
5. **Source indicator.** The active model shows its source ("via Vortex" /
   "via local") in the status strip.
6. **Chat routing.** A selected Vortex model routes chat through the Vortex
   universal endpoint (`router_chat_endpoint`); a local model routes through the
   existing local path. Default source = Vortex when `VORTEX_URL` is set.

## Out of scope (kept, not removed)

The legacy `SCRIPT_MODELS` + LM Studio default path stays as the fallback supply.
No legacy removal in this cutover.

## To launch the milestone (not done here)

Per D-139 this is CEO-gated: needs (a) the go, (b) a named TPM seat to author the
frozen tests, and (c) a memory window for the live cutover exercise (Testchat
chatting through Vortex with `qwen3.8-27b-8bit` loaded — the one-live-run-at-a-
time / free-RAM constraint).
