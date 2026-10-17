import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.model import ModelService
from app.schemas import ModelInfo, PredictRequest, PredictResponse

logging.basicConfig(level=logging.INFO)

model_service = ModelService(settings.model_path)


@asynccontextmanager
async def lifespan(_: FastAPI):
    model_service.load()
    yield


app = FastAPI(title="ML Inference API", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "model_loaded": model_service.loaded,
        "model_version": model_service.version,
    }


@app.get("/model", response_model=ModelInfo)
def model_info() -> ModelInfo:
    return model_service.info()


@app.post("/model/reload", response_model=ModelInfo)
def reload_model() -> ModelInfo:
    """Hot-reload the artifact after retraining, without restarting the service."""
    model_service.load()
    return model_service.info()


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest) -> PredictResponse:
    # Sync def -> FastAPI runs it in a threadpool, so CPU-bound inference doesn't block the loop.
    return PredictResponse(
        model_version=model_service.version, predictions=model_service.predict(req.records)
    )
