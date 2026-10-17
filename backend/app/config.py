from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_key: str = ""  # required; the app refuses to start without it
    # "mock", "http" (the ML microservice at ML_SERVICE_URL) or "package.module:ClassName"
    analyzer: str = "http"
    ml_service_url: str = "http://localhost:8001"
    data_dir: Path = Path("./data")  # uploads/ and jobs/ live here
    legal_mapping_file: Path = Path("./fortebank_violation_legal_mapping_updated.yaml")
    crosswalk_file: Path = Path("./specialist_crosswalk.yaml")
    max_upload_mb: int = 500
    allowed_extensions: list[str] = [".mov", ".mp4"]
    max_concurrent_jobs: int = 1
    # Upload to done/failed, queue time included. The jury counts a video as unprocessed after
    # 5 minutes, so this leaves margin for the upload and their polling interval.
    job_timeout_sec: float = 270.0
    min_confidence: float = 0.5  # violations below it become insufficient_evidence
    max_evidence_frames: int = 3
    ui_enabled: bool = True  # the simple web page and its key-less /ui/* endpoints
    # Key-less endpoints (/ui/*, /api/jobs/*) answer only local/private-network clients, so
    # exposing the service through a tunnel publishes /api/v1 and nothing else.
    local_only_ui: bool = True
    # Delete uploaded videos (not results) older than this; 0 keeps them.
    upload_retention_hours: float = 0
    # "supabase": every upload is also stored in a private Supabase Storage bucket (the local
    # copy stays as the analyzer's working file). "local": DATA_DIR/uploads only.
    storage_backend: Literal["supabase", "local"] = "supabase"
    supabase_url: str = ""
    supabase_key: str = ""  # service role / secret key: backend only, never sent to a browser
    supabase_bucket: str = "videos"
    signed_url_ttl_sec: int = 3600
    storage_timeout_sec: float = 120.0

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def jobs_dir(self) -> Path:
        return self.data_dir / "jobs"


settings = Settings()
