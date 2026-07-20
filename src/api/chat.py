import json
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, StrictStr

import src.services.llm as llm_mod
from src.services import websearch
from src.services.models import get_script_model, is_script_model_loaded


class HistoryEntry(BaseModel):
    role: Literal['user', 'assistant']
    content: str


class ChatRequest(BaseModel):
    message: str
    model: StrictStr | None = None
    history: list[HistoryEntry] = []
    web: bool = False


router = APIRouter()


@router.post("/api/v1/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    endpoint_override = None
    script_model = get_script_model(request.model) if request.model else None
    if script_model is not None:
        if not is_script_model_loaded(request.model):
            raise HTTPException(
                status_code=422, detail=f"Model {request.model} is not loaded"
            )
        endpoint_override = script_model["chat_endpoint"]

    # Sync generator on purpose: Starlette iterates it in a threadpool, so the
    # blocking urllib reads in stream_reply/search_web can't stall the event
    # loop (status polls and thread saves kept freezing during think gaps).
    def event_generator():
        history_dicts = [{"role": e.role, "content": e.content} for e in request.history]
        prompt_message = request.message
        if request.web:
            try:
                sources = websearch.search_web(request.message)
                numbered = [{"n": i + 1, "title": s["title"], "url": s["url"]} for i, s in enumerate(sources)]
                payload = json.dumps({"sources": numbered})
                yield f'event: sources\ndata: {payload}\n\n'.encode()
                prompt_message = websearch.build_prompt(request.message, sources)
            except websearch.WebSearchError:
                yield b'event: sources\ndata: {"sources": [], "notice": "web search unavailable"}\n\n'
        try:
            for item in llm_mod.stream_reply(prompt_message, history_dicts, endpoint_override, model=request.model):
                if item[0] == "token":
                    content = json.dumps(item[1])
                    yield f'event: token\ndata: {{"content": {content}}}\n\n'.encode()
                elif item[0] == "think":
                    content = json.dumps(item[1])
                    yield f'event: think\ndata: {{"content": {content}}}\n\n'.encode()
                elif item[0] == "done":
                    yield b'event: done\ndata: {}\n\n'
                elif item[0] == "error":
                    msg = json.dumps(item[1]) if len(item) > 1 else json.dumps(llm_mod.FALLBACK_REPLY)
                    yield f'event: error\ndata: {{"message": {msg}}}\n\n'.encode()
        except Exception as e:
            msg = json.dumps(str(e)) if str(e) else json.dumps(llm_mod.FALLBACK_REPLY)
            yield f'event: error\ndata: {{"message": {msg}}}\n\n'.encode()

    return StreamingResponse(event_generator(), media_type="text/event-stream")