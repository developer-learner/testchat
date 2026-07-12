from fastapi import APIRouter
from pydantic import BaseModel

from src.services.settings import load_settings, save_settings

router = APIRouter()


class SettingsPayload(BaseModel):
    system_prompt: str = ""


@router.get("/api/v1/settings")
def get_settings() -> dict:
    settings = load_settings()
    return {"system_prompt": settings.get("system_prompt", "")}


@router.put("/api/v1/settings")
def put_settings(payload: SettingsPayload) -> dict:
    settings = load_settings()
    settings["system_prompt"] = payload.system_prompt
    save_settings(settings)
    return {"status": "ok"}
