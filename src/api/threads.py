from typing import Literal
from fastapi import APIRouter
from pydantic import BaseModel

from src.services.storage import load_snapshot, quarantine_files, save_snapshot

router = APIRouter()


class HistoryEntry(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    ts: float = 0
    model: str = ""


class ThreadSnapshot(BaseModel):
    id: int
    title: str
    messages: list[HistoryEntry]
    model: str = ""
    locked: bool = False


class ThreadsPayload(BaseModel):
    threads: list[ThreadSnapshot]


@router.get("/api/v1/threads")
def get_threads():
    return {"threads": load_snapshot(), "quarantined": bool(quarantine_files())}


@router.put("/api/v1/threads")
def put_threads(payload: ThreadsPayload):
    save_snapshot([t.model_dump() for t in payload.threads])
    return {"status": "ok"}


@router.delete("/api/v1/threads")
def delete_threads():
    save_snapshot([])
    return {"status": "ok"}