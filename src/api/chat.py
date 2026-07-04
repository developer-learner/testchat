from fastapi import APIRouter
from pydantic import BaseModel

from src.services.echo import echo


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


router = APIRouter()


@router.post("/api/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    result = echo(request.message)
    return ChatResponse(reply=result)