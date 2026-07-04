# PRODUCT.md — Product Context

> Evergreen. Describes what we're building and who it's for.
> Not a task list — that's in tasks/. This is the "why" layer.

---

## Problem Statement

Operators running local LLMs via command-line servers (ollama, llama.cpp, vllm, LM Studio) have no simple browser-based chat interface. They either use the terminal or install heavyweight apps. testchat is a minimal FastAPI app that serves a chat UI and proxies messages to any OpenAI-compatible local endpoint.

---

## Target Users

| User type | Description | Primary need |
|-----------|-------------|--------------|
| Local LLM operator | Developer or hobbyist running models locally | Browser-based chat with their local model |

---

## Core Value Proposition

A single `uvicorn` command gives you a browser chat UI for any local LLM endpoint.

---

## What We Are Not Building

- Not a model manager — no downloading, loading, or switching models
- Not a multi-user app — no auth, no accounts, no persistence
- Not a prompt engineering tool — no system prompt UI, no templates
- Not a mobile app — desktop browser only

---

## Success Metrics

| Metric | Target | How measured |
|--------|--------|--------------|
| Time to first chat | Under 30 seconds from `uvicorn` to sending a message | Manual test |

---

## Feature Flags / Rollout Notes

| Feature | Status | Notes |
|---------|--------|-------|
| M1 Echo Chat | in-dev | Canned responses, no LLM |
| M2 Live LLM | planned | Real HTTP call to local endpoint |
| M3 Streaming | planned | SSE token-by-token |
| M4 History | planned | Conversation context |
