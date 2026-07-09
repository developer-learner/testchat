from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

try:
    from src.api.chat import router as chat_router

    app.include_router(chat_router)
except ImportError:
    pass

try:
    from src.api.models import router as models_router

    app.include_router(models_router)
except ImportError:
    pass

_INDEX = Path(__file__).parent / "static" / "index.html"


@app.get("/")
async def serve_index() -> HTMLResponse:
    return HTMLResponse(content=_INDEX.read_text())


app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")