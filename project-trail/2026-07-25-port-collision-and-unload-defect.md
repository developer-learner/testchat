# 2026-07-25 — a port choice killed a live chat, and what it uncovered

status: historical
seat: conductor (Claude Code, CEO session)

## What the operator saw

A chat that was working stopped working. No error banner, no crash, no
console clue pointing anywhere useful — the page stayed rendered, the
history stayed on screen, and messages simply stopped going anywhere. From
the CEO seat this looked like the app had broken itself.

The actual sequence, reconstructed afterwards:

1. The CEO asked whether testchat was running; it wasn't. The conductor
   started it with `uvicorn src.main:app --host 0.0.0.0 --port 8000`,
   having checked only that port 8000 was free at that moment.
2. Port 8000 is `DS4_URL` — DeepSeek's. The app **spawns that server
   itself** (`SCRIPT_MODELS[...]['command']`).
3. On the first model load, `ds4-server` bound `127.0.0.1:8000`. Because a
   specific address outranks a wildcard bind on BSD, the model server
   silently inherited `localhost:8000`.
4. Every `/api/v1/*` call from the open page then hit DeepSeek's API and
   came back `{"error": "unknown endpoint"}`.

The failure is silent by construction. Had the app bound `127.0.0.1`
instead, `ds4-server` would have failed loudly with `EADDRINUSE`. Verified
directly with a two-socket test rather than reasoned about:

| app binds | ds4 binds `127.0.0.1:8000` | result |
|---|---|---|
| `127.0.0.1:8000` | `FAILED: Address already in use` | load dies loudly at the 180s timeout |
| `0.0.0.0:8000` | `OK` | **silent hijack** |

So the collision is inherent to the documented default; only the *silent*
shape was the conductor's doing.

## The misdiagnosis worth recording

The CEO's opening framing was "RAM was full so I couldn't load a local
LLM," and the conductor initially chased a memory problem — including a
confident explanation that the 85 GB of `inactive` memory was `ds4-server`'s
mmap'd model weights. That was wrong: killing ds4 moved `free` from
0.3 → 5.2 GB while `inactive` went *up*, 85 → 90 GB. The conclusion (a
reclaimable cache, not consumption — the machine had ~95 GB available and
31 GB of total RSS against 128 GB installed) survived; the mechanism did
not. Recording it because the shape recurs: a plausible mechanism attached
to a correct conclusion reads as confirmation and escapes scrutiny.

The real ceiling for "won't load" on this machine is `iogpu.wired_limit_mb`
(unset = default ≈ 75% of RAM ≈ 96 GB), not free RAM. Two catalogued models
(`mistral-medium-3.5-128b`, `qwen3.5-122b-a10b`) brush that ceiling
regardless of how much memory is free.

## What it uncovered — the defect that was already there

Chasing the port problem surfaced a second, unrelated bug that had nothing
to do with the conductor. `unload_script_model` terminates only a process
it holds a live `subprocess.Popen` handle for, and those handles live in an
in-memory dict. After any app restart the spawned server is orphaned
(PPID 1) but still running — and unload returns `{"status": "unloaded"}`
anyway, having killed nothing. The catalog probes over HTTP and keeps
correctly reporting `loaded: true`. Permanent desync, no recovery from the
UI, `kill <pid>` by hand the only way out.

Isolated with a controlled A/B rather than asserted, because the honest
question was "is this the conductor's mess or the app's?":

| scenario | outcome |
|---|---|
| load → unload, same process | works: process gone, port freed, catalog accurate |
| load → **restart** → unload | API says `"unloaded"`, process still alive |

The restart in the second run was ordinary — kill, start again. **The
trigger is routine, not exotic: the documented run command is
`uvicorn src.main:app --reload`, which restarts the worker on every file
save.** Editing any source file while a script model is loaded orphans it.

Worse than the stuck button: `_unload_other_script_models` — the RAM
mutual-exclusion guarantee — detects the stale model correctly, calls
unload, receives a confident success, and loads the second model on top of
it. Two large script models resident at once, silently. That is a live path
to exactly the "RAM full" symptom the session opened with, though nothing
proves it is what happened this time.

## Dispositions

- Docs fix committed `4bdaa90` — app moved off 8000, port map recorded,
  correction-log row added. Mitigation only; nothing enforces it.
- Both defects filed in `tasks/BACKLOG.md`: unload-after-restart (P1),
  startup port guard (P2). Both are `src/` changes, so pipeline work.
- The unload fix's cheapest piece is the third one — stop returning
  `unloaded` unconditionally, re-probe after the kill attempt. It converts
  a silent lie into a visible error and can ship alone.

## The pattern

Three separate things in one evening had the same shape: a port conflict
that resolved silently instead of erroring, an unload endpoint that
reported success it never verified, and a documentation cadence
(`tasks/CURRENT.md`, "every session") that had lapsed six days and sixteen
commits without anyone noticing. Each is a check whose verdict nobody
consumes — the blueprint already names this in D-85: *a verdict nobody
consumes is not a gate*. The unload endpoint is the worst of the three,
because its verdict isn't merely unread — it's fabricated.
