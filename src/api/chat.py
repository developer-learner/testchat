import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.services.llm import stream_reply, FALLBACK_REPLY


class ChatRequest(BaseModel):
    message: str


router = APIRouter()


@router.post("/api/v1/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    async def event_generator():
        for item in stream_reply(request.message):
            if item[0] == "token":
                content = json.dumps(item[1])
                yield f'event: token\ndata: {{"content": {content}}}\n\n'.encode()
            elif item[0] == "done":
                yield b'event: done\ndata: {}\n\n'
            elif item[0] == "error":
                msg = json.dumps(FALLBACK_REPLY)
                yield f'event: error\ndata: {{"message": {msg}}}\n\n'.encode()

    return StreamingResponse(event_generator(), media_type="text/event-stream")