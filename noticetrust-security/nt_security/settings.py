import os
import tempfile
from dataclasses import dataclass


def _csv(name: str) -> tuple:
    return tuple(x.strip() for x in os.getenv(name, "").split(",") if x.strip())


@dataclass
class Settings:
    max_upload_bytes: int = 10 * 1024 * 1024      # PRD: JPEG/PNG up to 10 MB
    max_pixels: int = 25_000_000                   # decoded-pixel limit (decompression-bomb guard)
    max_dimension: int = 10_000                    # per-side limit
    storage_dir: str = os.path.join(tempfile.gettempdir(), "noticetrust_uploads")
    fallback_cleanup_seconds: int = 3600           # PRD: one-hour fallback cleanup
    sweep_interval_seconds: int = 300
    job_timeout_seconds: int = 60
    max_concurrent_jobs: int = 4
    upload_rate_limit: int = 10                    # uploads per window per IP
    read_rate_limit: int = 120                     # reads per window per IP
    rate_window_seconds: int = 60
    reviewer_token_hashes: tuple = ()              # sha256 hex of reviewer tokens
    allowed_origins: tuple = ()                    # explicit CORS origins, never "*"
    trust_proxy: bool = False                      # only True behind ONE trusted proxy
    enable_docs: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        d = cls()
        d.storage_dir = os.getenv("NT_STORAGE_DIR", d.storage_dir)
        d.reviewer_token_hashes = _csv("NT_REVIEWER_TOKEN_HASHES")
        d.allowed_origins = _csv("NT_ALLOWED_ORIGINS")
        d.trust_proxy = os.getenv("NT_TRUST_PROXY", "0") == "1"
        d.enable_docs = os.getenv("NT_ENABLE_DOCS", "0") == "1"
        return d
