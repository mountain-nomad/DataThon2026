"""Thin async client for the ML inference service."""

from typing import Any

import httpx
from fastapi import HTTPException

from app.config import settings


class MLClient:
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=settings.ml_service_url, timeout=settings.ml_timeout_seconds
        )

    async def stop(self) -> None:
        if self._client:
            await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        assert self._client is not None, "MLClient not started"
        try:
            resp = await self._client.request(method, path, **kwargs)
        except httpx.RequestError as e:
            raise HTTPException(503, f"ML service unreachable: {e}") from e
        if resp.is_error:
            raise HTTPException(502, f"ML service error {resp.status_code}: {resp.text}")
        return resp.json()

    async def health(self) -> dict:
        return await self._request("GET", "/health")

    async def model_info(self) -> dict:
        return await self._request("GET", "/model")

    async def predict(self, records: list[dict[str, Any]]) -> dict:
        return await self._request("POST", "/predict", json={"records": records})


ml_client = MLClient()
