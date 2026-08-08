# testchat

A minimal browser-based chat UI for local LLMs. FastAPI backend serves a chat page and proxies messages to any OpenAI-compatible local endpoint.

**Built with [sw-dev-blueprint](https://github.com/developer-learner/sw-dev-blueprint)** — the pipeline owns all procedure; tests are ground truth.

---

## Milestones

| Milestone | What it adds | Status |
|-----------|-------------|--------|
| M1 | Echo chat — canned responses, full stack wired | in-dev |
| M2 | Live LLM — real HTTP call to local endpoint | planned |
| M3 | Streaming — SSE token-by-token | planned |
| M4 | Conversation history — full context to LLM | planned |

---

## Quick start

```bash
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8080
# open http://localhost:8080
```

> **Do not run the app on port 8000.** That port is reserved for the DeepSeek
> script model (`ds4-server`, spawned by the app itself at `127.0.0.1:8000` —
> see `DS4_URL` in `src/services/models.py`). Binding the app there makes every
> DeepSeek load fail. 8080 is the project convention, matching
> `.claude/launch.json`.

---

## Project structure

```
testchat/
├── src/
│   ├── main.py              # FastAPI app + landing page
│   ├── api/
│   │   └── chat.py          # POST /api/v1/chat route
│   ├── services/
│   │   └── echo.py          # Echo responder (M1), LLM client (M2+)
│   └── static/
│       └── index.html       # Chat UI
├── tests/                   # TPM-authored, frozen
├── scripts/                 # Pipeline (orchestrate, gates, llm-call)
├── docs/                    # Architecture, decisions, product
└── tasks/                   # Current work + backlog
```

---

## How it works

See `BLUEPRINT.md` for the full pipeline. Short version:

1. TPM (frontier LLM) writes the spec and tests
2. TPM runs the refreeze — auto-applies when all mechanical preflights are green (no approval step, D-121)
3. `orchestrate.sh` drives EM (planner) and coder (local LLM) to build it
4. Frozen tests are ground truth — feature is done when the delta's mapped tests are green (D-112; full suite = on-demand `--full-suite` regression check)
