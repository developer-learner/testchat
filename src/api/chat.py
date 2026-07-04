from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from src.services.llm import generate_reply


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def root() -> HTMLResponse:
    return HTMLResponse(content="<html><body>Available routes: /api/v1/chat</body></html>")


@router.post("/api/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    result = generate_reply(request.message)
    return ChatResponse(reply=result)