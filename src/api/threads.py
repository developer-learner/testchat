from typing import Literal
from fastapi import APIRouter, JSONResponse
from pydantic import BaseModel, Field

from src.services.storage import (
    SnapshotConflict,
    load_versioned_snapshot,
    quarantine_files,
    save_versioned_snapshot,
)

router = APIRouter()


class SourceLink(BaseModel):
    title: str
    url: str


class HistoryEntry(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    ts: float = 0
    model: str = ""
    sources: list[SourceLink] | None = None


class ThreadSnapshot(BaseModel):
    id: int
    title: str
    messages: list[HistoryEntry]
    model: str = ""
    locked: bool = False


class ThreadsPayload(BaseModel):
    revision: int = Field(ge=0)
    threads: list[ThreadSnapshot]


class ThreadsRevisionPrecondition(BaseModel):
    revision: int = Field(ge=0)


@router.get("/api/v1/threads")
def get_threads():
    threads, revision = load_versioned_snapshot()
    return {"threads": threads, "revision": revision, "quarantined": bool(quarantine_files())}


@router.put("/api/v1/threads")
def put_threads(payload: ThreadsPayload):
    try:
        new_revision = save_versioned_snapshot(payload.threads, payload.revision)
    except SnapshotConflict as exc:
        return JSONResponse(
            status_code=409,
            content={"error": "revision_conflict", "current_revision": exc.current_revision},
        )
    return {"status": "ok", "revision": new_revision}


@router.delete("/api/v1/threads")
def delete_threads(body: ThreadsRevisionPrecondition):
    try:
        new_revision = save_versioned_snapshot([], body.revision)
    except SnapshotConflict as exc:
        return JSONResponse(
            status_code=409,
            content={"error": "revision_conflict", "current_revision": exc.current_revision},
        )
    return {"status": "ok", "revision": new_revision}