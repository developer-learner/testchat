from typing import Literal
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.services.storage import (
    SnapshotConflict,
    SnapshotUnavailableError,
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


class ThreadsListResponse(BaseModel):
    threads: list[ThreadSnapshot]
    revision: int
    quarantined: bool


class ThreadsPayload(BaseModel):
    revision: int = Field(ge=0)
    threads: list[ThreadSnapshot]


class ThreadsRevisionPrecondition(BaseModel):
    revision: int = Field(ge=0)


def _validate_snapshot_document(document) -> bool:
    if isinstance(document, dict):
        threads = document.get("threads")
        if not isinstance(threads, list):
            raise ValueError("threads not a list")
    elif isinstance(document, list):
        threads = document
    else:
        raise ValueError("invalid document shape")
    for item in threads:
        ThreadSnapshot.model_validate(item)
    return True


@router.get("/api/v1/threads")
def get_threads():
    try:
        threads, revision = load_versioned_snapshot(validator=_validate_snapshot_document)
    except SnapshotUnavailableError:
        return JSONResponse({"detail": "snapshot unavailable"}, status_code=503)
    quarantined = bool(quarantine_files())
    return ThreadsListResponse(threads=threads, revision=revision, quarantined=quarantined).model_dump(exclude_none=True)


@router.put("/api/v1/threads")
def put_threads(payload: ThreadsPayload):
    for t in payload.threads:
        for msg in t.messages:
            if msg.role not in ("user", "assistant"):
                return JSONResponse(content={"detail": "Invalid role"}, status_code=422)
    serialized = [t.model_dump(exclude_none=True) for t in payload.threads]
    for item in serialized:
        try:
            ThreadSnapshot(**item)
        except Exception:
            return JSONResponse(content={"detail": "Malformed payload"}, status_code=422)
    try:
        new_revision = save_versioned_snapshot(serialized, payload.revision)
    except SnapshotConflict as exc:
        return JSONResponse(
            status_code=409,
            content={"error": "revision_conflict", "current_revision": exc.current_revision},
        )
    return {"status": "ok", "revision": new_revision}


@router.delete("/api/v1/threads")
def delete_threads(body: ThreadsRevisionPrecondition | None = None):
    if body is None or not isinstance(body, ThreadsRevisionPrecondition):
        return JSONResponse(
            status_code=422,
            content={"detail": "Missing required field: revision"},
        )
    try:
        new_revision = save_versioned_snapshot([], body.revision)
    except SnapshotConflict as exc:
        return JSONResponse(
            status_code=409,
            content={"error": "revision_conflict", "current_revision": exc.current_revision},
        )
    return {"status": "ok", "revision": new_revision}