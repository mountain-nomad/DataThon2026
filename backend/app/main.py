from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import init_db
from app.ml_client import ml_client
from app.routers import health, predictions


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    await ml_client.start()
    yield
    await ml_client.stop()


app = FastAPI(title="Backend API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Everything lives under /api so the Next.js rewrite can proxy it 1:1.
app.include_router(health.router, prefix="/api")
app.include_router(predictions.router, prefix="/api")
