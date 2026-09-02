import json
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, StrictStr

import src.services.llm as llm_mod
import src.services.models as models_mod
from src.services import websearch
from src.services.models import get_script_model, is_script_model_loaded


class HistoryEntry(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., max_length=32_000)
    model: StrictStr | None = None
    history: list[HistoryEntry] = Field(default_factory=list, max_length=100)
    web: bool = False


router = APIRouter()


@router.post("/api/v1/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    endpoint_override = None
    # Guard on request.model itself, not on the derived script_model: both
    # reads below need it narrowed to str, and mypy cannot infer that a
    # non-None script_model implies a non-None request.model.
    if request.model:
        script_model = get_script_model(request.model)
        if script_model is not None:
            if not is_script_model_loaded(request.model):
                raise HTTPException(
                    status_code=422, detail=f"Model {request.model} is not loaded"
                )
            endpoint_override = script_model["chat_endpoint"]
        elif models_mod.is_router_configured() and models_mod.is_router_model(request.model):
            endpoint_override = models_mod.router_chat_endpoint()

    # Sync generator on purpose: Starlette iterates it in a threadpool, so the
    # blocking urllib reads in stream_reply/search_web can't stall the event
    # loop (status polls and thread saves kept freezing during think gaps).
    def event_generator():
        history_dicts = [
            {"role": e.role, "content": e.content} for e in request.history
        ]
        prompt_message = request.message
        if request.web:
            try:
                sources = websearch.search_web(request.message)
                numbered = [
                    {"n": i + 1, "title": s["title"], "url": s["url"]}
                    for i, s in enumerate(sources)
                ]
                payload = json.dumps({"sources": numbered})
                yield f"event: sources\ndata: {payload}\n\n".encode()
                prompt_message = websearch.build_prompt(request.message, sources)
            except websearch.WebSearchError:
                yield b'event: sources\ndata: {"sources": [], "notice": "web search unavailable"}\n\n'
        try:
            for item in llm_mod.stream_reply(
                prompt_message, history_dicts, endpoint_override, model=request.model
            ):
                if item[0] == "token":
                    content = json.dumps(item[1])
                    yield f'event: token\ndata: {{"content": {content}}}\n\n'.encode()
                elif item[0] == "think":
                    content = json.dumps(item[1])
                    yield f'event: think\ndata: {{"content": {content}}}\n\n'.encode()
                elif item[0] == "done":
                    yield b"event: done\ndata: {}\n\n"
                elif item[0] == "error":
                    msg = (
                        json.dumps(item[1])
                        if len(item) > 1
                        else json.dumps(llm_mod.FALLBACK_REPLY)
                    )
                    yield f'event: error\ndata: {{"message": {msg}}}\n\n'.encode()
        except (ConnectionError, TimeoutError, OSError) as e:
            if not str(e) and endpoint_override:
                if not models_mod.is_router_model(request.model):
                    msg = json.dumps(f"Model {request.model} is not ready in Vortex. Pick a local model or retry once it is loaded.")
                    yield f'event: error\ndata: {{"message": {msg}}}\n\n'.encode()
                else:
                    msg = json.dumps(llm_mod.FALLBACK_REPLY)
                    yield f'event: error\ndata: {{"message": {msg}}}\n\n'.encode()
            else:
                msg = json.dumps(str(e)) if str(e) else json.dumps(llm_mod.FALLBACK_REPLY)
                yield f'event: error\ndata: {{"message": {msg}}}\n\n'.encode()

    return StreamingResponse(event_generator(), media_type="text/event-stream")
