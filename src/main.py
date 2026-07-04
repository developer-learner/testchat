from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

try:
    from src.api.chat import router as chat_router

    app.include_router(chat_router)
except ImportError:
    pass


@app.get("/")
async def serve_index() -> HTMLResponse:
    return HTMLResponse(
        content="<html><body><p>/api/v1/chat</p></body></html>"
    )