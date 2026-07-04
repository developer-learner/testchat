from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

app = FastAPI()

_INDEX_HTML = Path(__file__).resolve().parent / "static" / "index.html"


@app.get("/")
async def serve_index():
    return FileResponse(_INDEX_HTML)


try:
    from src.api.chat import router as chat_router

    app.include_router(chat_router)
except ImportError:
    pass