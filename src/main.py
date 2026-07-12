from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()


@app.middleware("http")
async def no_stale_static(request: Request, call_next) -> Response:
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static"):
        response.headers["Cache-Control"] = "no-cache"
    return response

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

try:
    from src.api.threads import router as threads_router

    app.include_router(threads_router)
except ImportError:
    pass

_INDEX = Path(__file__).parent / "static" / "index.html"


@app.get("/")
async def serve_index() -> HTMLResponse:
    return HTMLResponse(content=_INDEX.read_text())


app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")