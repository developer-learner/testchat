PRD — testchat M6: Multichat (In-Memory Threads)

Milestone
M6. Adds multiple simultaneous conversations to the existing single-chat UI.
Each conversation ("thread") has its own message history, model selection, and
model-lock state. All threads live in-memory only — page refresh clears
everything (same as M1–M5). This is a frontend-only milestone: no backend
routes are added or changed.

What

Frontend (src/static/index.html):

A left sidebar listing all conversation threads. Each entry shows the thread
title (auto-derived from the first user message, truncated to ~40 characters).
A "New Chat" button at the top of the sidebar creates a fresh thread with an
empty history and unlocked model selector.

The right panel is the existing chat container — messages, input area, think
toggle — now scoped to whichever thread is selected in the sidebar. Switching
threads swaps the visible messages, the model selector value, and the lock
state. The think-toggle remains global (user preference, not per-thread).

On page load, one thread is created automatically (equivalent to today's
single-conversation state), so the UI never shows an empty right panel.

Per-thread state:
- messages (DOM bubbles + the conversation history array sent to the API)
- selected model (the value of the model-select dropdown)
- model-lock (whether the selector is disabled — locked after first send)
- title (first user message, truncated, or "New Chat" if no messages yet)

Global state (unchanged from M5):
- Nemotron load/unload (one process, shared across threads)
- Model list (GET /api/v1/models — same list populates every thread's selector)
- Think-toggle on/off
- FALLBACK_REPLY constant

Switching threads while a stream is in progress: the active stream continues
writing to its thread's state in the background. The user sees the target
thread's messages immediately. When they switch back, the completed (or
still-streaming) reply is visible. There is no cancellation — the SSE
connection stays open until done/error.

Acceptance Criteria (EARS notation)
All M3, M4, and M5 acceptance criteria remain in force. The criteria below are
additive. All are frontend-only (CEO-demo-verified unless otherwise noted).

Sidebar:
AC-18: WHEN the page loads, THE SYSTEM SHALL display a sidebar with one
default thread titled "New Chat" and the chat panel showing that thread.
AC-19: WHEN the user clicks "New Chat", THE SYSTEM SHALL create a new thread
with an empty history, an unlocked model selector, and switch to it.
AC-20: WHEN the user clicks a thread in the sidebar, THE SYSTEM SHALL display
that thread's messages, model selection, and lock state in the chat panel.
AC-21: WHEN the user sends the first message in a thread titled "New Chat",
THE SYSTEM SHALL update the thread's sidebar title to the first ~40 characters
of that message.

Thread isolation:
AC-22: WHEN the user sends messages in thread A then switches to thread B,
THE SYSTEM SHALL show thread B's messages (which may be empty) and thread B's
model selector state, with thread A's state preserved.
AC-23: WHEN the user has locked the model in thread A by sending a message,
THE SYSTEM SHALL keep the model selector unlocked in a new thread B that has
not yet sent a message.
AC-24: WHEN a stream is in progress in thread A and the user switches to
thread B, THE SYSTEM SHALL continue receiving thread A's stream in the
background and display thread B's current state in the panel.

Existing behavior preserved:
AC-25: WHEN the page is refreshed, THE SYSTEM SHALL clear all threads and
start with a single fresh "New Chat" thread (no persistence).
AC-26: WHEN the user loads or unloads Nemotron, THE SYSTEM SHALL update the
model list globally — the change is reflected in whichever thread is currently
visible and in any thread the user switches to afterward.

Out of Scope

Persistence (localStorage, backend storage, or any survival across refresh).
Thread deletion or renaming (beyond auto-title from first message).
Thread reordering or drag-and-drop.
Search across threads.
Any backend changes — no new routes, no new API fields, no changes to
POST /api/v1/chat or GET /api/v1/models.
Any change to SSE wire format, streaming behavior, or failure handling.
Thread-level Nemotron controls (load/unload is global).

Flagged Assumptions (CEO sign-off before freeze)

A7: A single SSE connection per in-flight request is acceptable — no
multiplexing or WebSocket upgrade. Thread-switching while streaming leaves the
connection alive; it writes into the thread's in-memory state.
A8: Auto-title from the first message (truncated at ~40 chars, no
intelligence) is sufficient — no LLM-generated titles.
A9: The sidebar is always visible (no collapsible/hamburger mode). Mobile
responsiveness is out of scope for M6.
A10: The "New Chat" button is always enabled — there is no limit on thread
count. Memory growth is bounded by the user's willingness to keep chatting
before refresh.

CEO Demo Script

Open the page — confirm one "New Chat" thread in the sidebar, chat panel empty.
Send a message — confirm the sidebar title updates to the first ~40 chars.
Click "New Chat" — confirm a second thread appears, panel clears, model
selector unlocks.
Switch between threads — confirm each has its own messages and model state.
In thread 1, select Nemotron and send a message (model locks). Switch to
thread 2 — confirm model selector is unlocked and defaults to whatever the
model list shows.
Start a long reply in thread 1, switch to thread 2 while it streams, switch
back — confirm the completed reply is visible in thread 1.
Refresh the page — confirm everything is cleared, single "New Chat" thread.
