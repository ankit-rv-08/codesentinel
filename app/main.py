"""FastAPI entry point."""

from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI

from app.api.stats import router as stats_router
from app.db import init_db
from app.github.webhook import router as webhook_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="CodeSentinel", lifespan=lifespan)

app.include_router(webhook_router)
app.include_router(stats_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "codesentinel"}
