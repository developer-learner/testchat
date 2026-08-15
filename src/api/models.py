import logging
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from src.services.models import (
    SCRIPT_MODELS,
    list_model_catalog,
    list_models,
    load_script_model,
    unload_script_model,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")


class ModelInfo(BaseModel):
    id: str
    source: Literal[
        "lmstudio", "nemotron", "deepseek-v4-flash-0731", "Flash_Q2KXL", "Flash_IQ3XXS"
    ]


class ModelsListResponse(BaseModel):
    models: list[ModelInfo]


class ScriptModelLoadResponse(BaseModel):
    status: Literal["loaded", "error"]
    message: Optional[str] = None


class ScriptModelUnloadResponse(BaseModel):
    status: Literal["unloaded", "error"]
    message: Optional[str] = None


class CatalogEntry(BaseModel):
    id: str
    source: Literal["nemotron", "deepseek-v4-flash-0731", "Flash_Q2KXL", "Flash_IQ3XXS"]
    loaded: bool


class ModelCatalogResponse(BaseModel):
    models: list[CatalogEntry]


# Back-compat aliases for the historical nemotron-specific response names.
NemotronLoadResponse = ScriptModelLoadResponse
NemotronUnloadResponse = ScriptModelUnloadResponse


# These list endpoints run blocking readiness probes (list_models hits LM Studio
# and each script model's ready_url with a ~2s httpx timeout). As `async def`
# that blocking ran on the event loop and stalled every concurrent request up to
# ~2s per unreachable model; as plain `def` FastAPI runs them in the threadpool,
# off the loop — the same fix class as the AC-165 load/unload endpoints.
@router.get("/models")
def get_models() -> ModelsListResponse:
    models = list_models()
    return ModelsListResponse(models=[ModelInfo(**m) for m in models])


@router.get("/models/catalog")
def get_model_catalog() -> ModelCatalogResponse:
    return ModelCatalogResponse(
        models=[CatalogEntry(**m) for m in list_model_catalog()]
    )


def _require_script_model(model_id: str) -> None:
    if model_id not in SCRIPT_MODELS:
        raise HTTPException(status_code=404, detail=f"Unknown script model: {model_id}")


def _load_response(model_id: str) -> Response:
    result = load_script_model(model_id)
    status_code = 503 if result["status"] == "error" else 200
    return JSONResponse(
        status_code=status_code, content=ScriptModelLoadResponse(**result).model_dump()
    )


def _unload_response(model_id: str) -> Response:
    result = unload_script_model(model_id)
    status_code = 503 if result["status"] == "error" else 200
    return JSONResponse(
        status_code=status_code,
        content=ScriptModelUnloadResponse(**result).model_dump(),
    )


@router.post("/script-models/{model_id}/load", response_model=ScriptModelLoadResponse)
def load_script_model_endpoint(model_id: str) -> Response:
    _require_script_model(model_id)
    return _load_response(model_id)


@router.post(
    "/script-models/{model_id}/unload", response_model=ScriptModelUnloadResponse
)
def unload_script_model_endpoint(model_id: str) -> Response:
    _require_script_model(model_id)
    return _unload_response(model_id)


@router.post("/nemotron/load", response_model=ScriptModelLoadResponse)
def load_nemotron_model() -> Response:
    return _load_response("nemotron")


@router.post("/nemotron/unload", response_model=ScriptModelUnloadResponse)
def unload_nemotron_model() -> Response:
    return _unload_response("nemotron")
