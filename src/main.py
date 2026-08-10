from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response

from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# Load .env BEFORE importing the routers. src/services/models.py reads
# NEMOTRON_URL / DS4_URL / DS4_0731_URL at import time (module-level), so the
# values must already be in os.environ when that import runs — calling
# load_dotenv() after the imports would be too late for those config reads.
load_dotenv()

from src.api.chat import router as chat_router  # noqa: E402
from src.api.models import router as models_router  # noqa: E402
from src.api.settings import router as settings_router  # noqa: E402
from src.api.status import router as status_router  # noqa: E402
from src.api.threads import router as threads_router  # noqa: E402

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
