from fastapi import APIRouter, HTTPException

from app.ml_client import ml_client

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    try:
        ml = await ml_client.health()
    except HTTPException as e:
        ml = {"status": "down", "detail": e.detail}
    return {"status": "ok", "ml": ml}


@router.get("/model")
async def model_info() -> dict:
    return await ml_client.model_info()
