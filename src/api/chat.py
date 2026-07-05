import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator

from src.services.llm import stream_reply, FALLBACK_REPLY


class ChatHistoryEntry(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatHistoryEntry] = []

    @field_validator("history")
    @classmethod
    def validate_history_roles(cls, v):
        for entry in v:
            if entry.role not in ("user", "assistant"):
                raise ValueError("history entries must have role 'user' or 'assistant'")
        return v


router = APIRouter()


@router.post("/api/v1/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    async def event_generator():
        history_dicts = [{"role": e.role, "content": e.content} for e in request.history]
        for item in stream_reply(request.message, history=history_dicts):
            if item[0] == "token":
                content = json.dumps(item[1])
                yield f'event: token\ndata: {{"content": {content}}}\n\n'.encode()
            elif item[0] == "done":
                yield b'event: done\ndata: {}\n\n'
            elif item[0] == "error":
                msg = json.dumps(FALLBACK_REPLY)
                yield f'event: error\ndata: {{"message": {msg}}}\n\n'.encode()

    return StreamingResponse(event_generator(), media_type="text/event-stream")