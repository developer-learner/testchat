from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response

from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from src.api.chat import router as chat_router
from src.api.models import router as models_router
from src.api.settings import router as settings_router
from src.api.status import router as status_router
from src.api.threads import router as threads_router

load_dotenv()  # repo convention: runtime config via .env (TAVILY_API_KEY etc.)

app = FastAPI()


@app.middleware("http")
async def no_stale_static(request: Request, call_next) -> Response:
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static"):
        response.headers["Cache-Control"] = "no-cache"
    return response


app.include_router(chat_router)
app.include_router(models_router)
app.include_router(threads_router)
app.include_router(status_router)
app.include_router(settings_router)


_INDEX = Path(__file__).parent / "static" / "index.html"


@app.get("/")
async def serve_index() -> HTMLResponse:
    return HTMLResponse(content=_INDEX.read_text())


app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")
