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
uvicorn src.main:app --reload --host 127.0.0.1 --port 8010
# open http://localhost:8010
```

> **Do not run the app on port 8000.** That port belongs to the DeepSeek script
> model (`DS4_URL`, default `http://127.0.0.1:8000`) — which the app launches
> itself. Loading DeepSeek while the app sits on 8000 lets `ds4-server` bind the
> same port and silently take over `localhost`, breaking the UI mid-session.
> See `CLAUDE.md` → Commands for the full failure mode.

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
2. CEO approves the freeze
3. `orchestrate.sh` drives EM (planner) and coder (local LLM) to build it
4. Frozen tests are ground truth — feature is done when the full suite is green
