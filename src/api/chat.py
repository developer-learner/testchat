from fastapi import APIRouter
from pydantic import BaseModel

from loguru import logger


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


router = APIRouter()


@router.post("/api/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    from src.services.echo import echo

    logger.info("Received chat request: message={}", request.message)
    result = echo(request.message)
    logger.info("Chat response: reply={}", result)
    return ChatResponse(reply=result)