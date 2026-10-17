"""Where uploaded videos are kept: Supabase Storage (private bucket) or nowhere besides the disk.

The upload is always streamed and validated on local disk first (the analyzer and OpenCV need a
file path); `save()` then copies it to the object store. A job keeps the object key, which is
stable, and asks for a short-lived signed URL whenever someone needs to fetch the video.
"""

import logging
from datetime import UTC, datetime
from functools import cache
from pathlib import Path
from typing import Protocol

import httpx
from storage3.utils import StorageException
from supabase import ClientOptions, create_client

from app.config import settings

log = logging.getLogger(__name__)


# API errors, network/timeouts, and the local file being unreadable.
_ERRORS = (StorageException, httpx.HTTPError, OSError)


class StorageError(Exception):
    """The object store refused or failed a request."""


class VideoStorage(Protocol):
    def ensure_ready(self) -> None: ...
    def save(self, local_path: Path, key: str) -> str | None: ...
    def signed_url(self, key: str) -> str | None: ...
    def delete(self, key: str) -> None: ...


def object_key(job_id: str, ext: str) -> str:
    """Unique by job id; the client's file name never becomes part of the key."""
    now = datetime.now(UTC)
    return f"{now:%Y/%m}/{job_id}{ext}"


class LocalStorage:
    """No remote copy: the video stays only in DATA_DIR/uploads."""

    def ensure_ready(self) -> None:
        pass

    def save(self, local_path: Path, key: str) -> str | None:
        return None

    def signed_url(self, key: str) -> str | None:
        return None

    def delete(self, key: str) -> None:
        pass


class SupabaseStorage:
    def __init__(self) -> None:
        client = create_client(
            settings.supabase_url,
            settings.supabase_key,
            # Uploads are tens of MB; the 20 s default is too short on a slow uplink.
            ClientOptions(storage_client_timeout=settings.storage_timeout_sec),
        )
        self._storage = client.storage
        self._bucket = settings.supabase_bucket

    def ensure_ready(self) -> None:
        """Create the private bucket on first start."""
        try:
            names = {b.id for b in self._storage.list_buckets()}
            if self._bucket not in names:
                self._storage.create_bucket(self._bucket, options={"public": False})
                log.info("Created private Supabase bucket %r", self._bucket)
        except _ERRORS as e:
            raise StorageError(f"Supabase bucket {self._bucket!r} is not usable: {e}") from e

    def save(self, local_path: Path, key: str) -> str:
        try:
            self._storage.from_(self._bucket).upload(
                key,
                local_path,
                # H.264 .mov plays in browsers when labelled video/mp4; the bytes are unchanged.
                {"content-type": "video/mp4", "upsert": "false"},
            )
        except _ERRORS as e:
            raise StorageError(str(e)) from e
        return key

    def signed_url(self, key: str) -> str:
        try:
            res = self._storage.from_(self._bucket).create_signed_url(
                key, settings.signed_url_ttl_sec
            )
        except _ERRORS as e:
            raise StorageError(str(e)) from e
        if not res.get("signedURL"):
            raise StorageError(f"No signed URL for {key}")
        return res["signedURL"]

    def delete(self, key: str) -> None:
        try:
            self._storage.from_(self._bucket).remove([key])
        except _ERRORS as e:
            raise StorageError(str(e)) from e


@cache
def get_storage() -> VideoStorage:
    if settings.storage_backend == "supabase":
        if not settings.supabase_url or not settings.supabase_key:
            raise RuntimeError(
                "STORAGE_BACKEND=supabase needs SUPABASE_URL and SUPABASE_KEY (service role) in .env"
            )
        return SupabaseStorage()
    return LocalStorage()
