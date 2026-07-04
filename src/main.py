from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

try:
    from src.api.chat import router as chat_router

    app.include_router(chat_router)
except ImportError:
    pass

_INDEX = Path(__file__).parent / "static" / "index.html"


@app.get("/")
async def serve_index() -> HTMLResponse:
    return HTMLResponse(content=_INDEX.read_text())