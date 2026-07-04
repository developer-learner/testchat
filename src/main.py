import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

# Resolve static file relative to this module's location (not cwd)
_INDEX_HTML = Path(__file__).resolve().parent / "static" / "index.html"


@app.get("/")
async def serve_index() -> HTMLResponse:
    html_content = _INDEX_HTML.read_text(encoding="utf-8")
    return HTMLResponse(content=html_content)


try:
    from src.api.chat import router

    app.include_router(router)
except ImportError:
    pass