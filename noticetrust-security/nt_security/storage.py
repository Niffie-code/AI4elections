"""Private temporary upload storage with two cleanup paths."""
import os
import re
import time
from pathlib import Path

_JOB_ID = re.compile(r"[0-9a-f]{32}")


class PrivateStorage:
    def __init__(self, root: str):
        self.root = Path(root)
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)

    def _check(self, job_id: str):
        if not _JOB_ID.fullmatch(job_id):          # blocks path traversal via ids
            raise ValueError("invalid job id")

    def save(self, job_id: str, data: bytes, ext: str) -> Path:
        self._check(job_id)
        path = self.root / f"{job_id}{ext}"
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        return path

    def delete(self, job_id: str) -> int:
        """Cleanup path 1: called in `finally` right after processing."""
        self._check(job_id)
        n = 0
        for p in self.root.glob(f"{job_id}.*"):
            try:
                p.unlink()
                n += 1
            except FileNotFoundError:
                pass
        return n

    def sweep(self, max_age_s: int) -> int:
        """Cleanup path 2: fallback for crashed/failed jobs (default: older than 1 hour)."""
        cutoff, n = time.time() - max_age_s, 0
        for p in self.root.iterdir():
            try:
                if p.is_file() and p.stat().st_mtime < cutoff:
                    p.unlink()
                    n += 1
            except FileNotFoundError:
                pass
        return n
