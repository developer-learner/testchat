from fastapi import FastAPI
app = FastAPI()
try:
    from src.api.chat import router
    app.include_router(router)
except ImportError:
    pass
