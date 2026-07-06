import json
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import src.services.llm as llm_mod
from src.services.models import is_nemotron_loaded, NEMOTRON_CHAT_ENDPOINT


class HistoryEntry(BaseModel):
    role: Literal['user', 'assistant']
    content: str


class ChatRequest(BaseModel):
    message: str
    model: str | None = None
    history: list[HistoryEntry] = []


router = APIRouter()


@router.post("/api/v1/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    if request.model == "nemotron" and not is_nemotron_loaded():
        raise HTTPException(status_code=422, detail="Nemotron model is not loaded")

    endpoint_override = NEMOTRON_CHAT_ENDPOINT if request.model == "nemotron" else None

    async def event_generator():
        history_dicts = [{"role": e.role, "content": e.content} for e in request.history]
        try:
            for item in llm_mod.stream_reply(request.message, history_dicts, endpoint_override):
                if item[0] == "token":
                    content = json.dumps(item[1])
                    yield f'event: token\ndata: {{"content": {content}}}\n\n'.encode()
                elif item[0] == "done":
                    yield b'event: done\ndata: {}\n\n'
                elif item[0] == "error":
                    msg = json.dumps(item[1]) if len(item) > 1 else json.dumps(llm_mod.FALLBACK_REPLY)
                    yield f'event: error\ndata: {{"message": {msg}}}\n\n'.encode()
        except Exception as e:
            msg = json.dumps(str(e)) if str(e) else json.dumps(llm_mod.FALLBACK_REPLY)
            yield f'event: error\ndata: {{"message": {msg}}}\n\n'.encode()

    return StreamingResponse(event_generator(), media_type="text/event-stream")