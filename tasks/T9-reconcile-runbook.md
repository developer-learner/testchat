# Control-plane reconcile runbook — Testchat + Vortex (2026-09-01)

Prep on branch `t9-cutover-prep` (worktree `~/dev/testchat-t9`), isolated from the
shared Blueprint checkout that Track C is actively committing to. This runbook is
**ready to fire**; it is blocked ONLY on the precondition below.

## Corrected diagnosis (re-derived from disk, not from prior narrative)

The shared Blueprint checkout (`~/dev/sw-dev-blueprint`) advanced; both children
symlink into it and both frozen manifests now lag — **each on a different file**:

| Child    | Gate red on            | Manifest expects | Symlink resolves to |
|----------|------------------------|------------------|---------------------|
| Testchat | `.opencode/prompts/coder.md` | `c00fc61…`  | `ac49c20…`          |
| Vortex   | `scripts/bootstrap.sh` | `1c137b1…`       | `5282321…`          |

The earlier blocker ("shared checkout dirty on manifested `scripts/llm-call.sh`")
is **stale/false** — `llm-call.sh` is clean and committed.

## Precondition (the ONLY thing blocking the reconcile)

Track C is live on the shared Blueprint. At last check HEAD `8318630` was
**committed but NOT pushed** (ahead of `origin/main` by 1) and moving. Do NOT
reconcile until ALL of:

```bash
cd ~/dev/sw-dev-blueprint
git status --porcelain=v1        # must be EMPTY (clean working tree)
[ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] && echo PUSHED || echo NOT-PUSHED
```

Must read: clean tree **and** `PUSHED`. Children's CI verifies against a fresh
clone of the template **from origin**, so adopting an unpushed tip goes green
locally then fails CI. Also confirm Track C has *stopped* editing (HEAD stable
across two checks a minute apart) — the ref must not move mid-adopt.

Both children share the ONE Blueprint checkout, so they MUST adopt the SAME ref.

## The reconcile (per child, once precondition holds)

`regen-manifest.sh` re-hashes EVERY entry to match current linked content (by
design — partial updates are how silent drift happened before). Run from repo root:

```bash
# Testchat
cd ~/dev/testchat-t9            # or ~/dev/testchat once merged
bash scripts/regen-manifest.sh scripts/.manifest-template
bash ~/dev/sw-dev-blueprint/scripts/phase-gate.sh manifest HEAD   # expect: no GATE FAIL
git add scripts/.manifest-template tasks/T9-cutover-design.md tasks/T9-reconcile-runbook.md
git commit -m "reconcile: re-adopt Blueprint control plane at <ref>; record T9 cutover design"

# Vortex (separate driver / separate pass — one driver per repo main)
cd ~/dev/vortex
bash scripts/regen-manifest.sh scripts/.manifest-template
bash ~/dev/sw-dev-blueprint/scripts/phase-gate.sh manifest HEAD   # expect: no GATE FAIL
git commit -am "reconcile: re-adopt Blueprint control plane at <ref>"
```

Substitute `<ref>` with the actual pushed Blueprint short SHA.

## After reconcile — merge this prep branch

`t9-cutover-prep` was cut from Testchat `main` @ `7743201`. Fast-forward `main`
to it (or cherry-pick the two `tasks/` notes + the manifest change), push, then
`git worktree remove ~/dev/testchat-t9`.

## Still gated downstream (NOT part of this reconcile)

- **T9 milestone launch** is CEO-gated (D-139): needs the go, a named TPM seat to
  author the frozen tests, and a memory window for the live cutover run
  (one-live-run-at-a-time / free-RAM). See `T9-cutover-design.md` for the target.
