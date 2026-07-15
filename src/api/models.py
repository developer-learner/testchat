import logging
from typing import Literal, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from src.services.models import list_models, load_nemotron, unload_nemotron

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")


class ModelInfo(BaseModel):
    id: str
    source: Literal["lmstudio", "nemotron"]


class ModelsListResponse(BaseModel):
    models: list[ModelInfo]


class NemotronLoadResponse(BaseModel):
    status: Literal["loaded", "error"]
    message: Optional[str] = None


class NemotronUnloadResponse(BaseModel):
    status: Literal["unloaded", "error"]
    message: Optional[str] = None


@router.get("/models")
async def get_models() -> ModelsListResponse:
    models = list_models()
    return ModelsListResponse(models=[ModelInfo(**m) for m in models])


@router.post("/nemotron/load", response_model=NemotronLoadResponse)
async def load_nemotron_model() -> Response:
    result = load_nemotron()
    if result["status"] == "error":
        return JSONResponse(status_code=503, content=NemotronLoadResponse(**result).model_dump())
    return JSONResponse(status_code=200, content=NemotronLoadResponse(**result).model_dump())


@router.post("/nemotron/unload", response_model=NemotronUnloadResponse)
async def unload_nemotron_model() -> Response:
    result = unload_nemotron()
    return JSONResponse(status_code=200, content=NemotronUnloadResponse(**result).model_dump())