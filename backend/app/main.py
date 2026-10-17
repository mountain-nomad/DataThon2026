import asyncio
import ipaddress
import logging
from contextlib import asynccontextmanager, suppress
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import jobs
from app.api import api, frontend, ui
from app.config import settings
from app.legal import load_legal
from app.storage import get_storage
from app.worker import Worker

STATIC_DIR = Path(__file__).parent / "static"
# Reachable from anywhere (the jury); everything else is local-only, see local_only_ui.
PUBLIC_PATHS = ("/api/v1/", "/health", "/docs", "/openapi.json")
# Headers tunnels and reverse proxies use to pass on the real client address.
CLIENT_IP_HEADERS = ("x-forwarded-for", "x-real-ip", "cf-connecting-ip", "true-client-ip")

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


async def _cleanup_loop() -> None:
    while True:
        await asyncio.to_thread(jobs.delete_old_uploads)  # may call the object store
        await asyncio.sleep(3600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.api_key:
        raise RuntimeError("API_KEY is not set. Copy .env.example to .env and set it.")
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.jobs_dir.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(get_storage().ensure_ready)  # fails fast on a bad Supabase config
    jobs.fail_interrupted()
    app.state.worker = Worker(load_legal(settings.legal_mapping_file, settings.crosswalk_file))
    app.state.worker.start()
    cleanup = asyncio.create_task(_cleanup_loop())
    yield
    cleanup.cancel()
    with suppress(asyncio.CancelledError):
        await cleanup
    app.state.worker.stop()


app = FastAPI(title="Cash desk video analysis", version="0.1.0", lifespan=lifespan)


def _is_local(request: Request) -> bool:
    """The client and every address a proxy reports for it are loopback or private-network.

    A tunnel (cloudflared, ngrok) connects from localhost but reports the real client in these
    headers, so tunneled requests count as remote. The Next.js dev proxy reports the browser's
    local address, so the frontend keeps working.
    """
    addresses = [request.client.host if request.client else ""]
    for header in CLIENT_IP_HEADERS:
        addresses += [a.strip() for a in request.headers.get(header, "").split(",") if a.strip()]
    try:
        return all((ip := ipaddress.ip_address(a)).is_loopback or ip.is_private for a in addresses)
    except ValueError:
        return False


@app.middleware("http")
async def local_only(request: Request, call_next):
    path = request.url.path
    if settings.local_only_ui and not path.startswith(PUBLIC_PATHS) and not _is_local(request):
        return JSONResponse({"detail": "Not Found"}, status_code=404)
    return await call_next(request)


app.include_router(api)
app.include_router(frontend)


@app.get("/health", include_in_schema=False)
async def health() -> dict:
    out = {"status": "ok", "analyzer": settings.analyzer, "storage": settings.storage_backend}
    if settings.analyzer == "http":
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                out["ml"] = (await client.get(f"{settings.ml_service_url}/health")).json()
        except (httpx.HTTPError, ValueError) as e:
            out["ml"] = {"status": "down", "detail": str(e) or type(e).__name__}
    return out


if settings.ui_enabled:
    app.include_router(ui)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")
