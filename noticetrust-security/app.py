"""Reference wiring of the security controls onto the PRD's API contract.

Backend owner: replace `run_pipeline` with the real OCR/retrieval/comparison call and the
in-memory JOBS dict with PostgreSQL. Keep the Depends(...) guards and the `finally` cleanup.
"""
import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from nt_security.auth import check_job_token, make_reviewer_dependency
from nt_security.logsafe import install_redaction
from nt_security.middleware import BodyLimitMiddleware, SecurityHeadersMiddleware
from nt_security.ratelimit import RateLimiter
from nt_security.settings import Settings
from nt_security.storage import PrivateStorage
from nt_security.tokens import issue_job
from nt_security.upload import read_limited, validate_and_clean_image

log = logging.getLogger("noticetrust")
NOT_FOUND = HTTPException(404, "Not found.")   # same answer for "missing" and "not yours"


async def run_pipeline(path) -> dict:
    """STUB for Workstream B. Treat all OCR text as untrusted data, never as instructions."""
    await asyncio.sleep(0.05)
    return {"outcome": "unable_to_verify", "reason_codes": ["PIPELINE_STUB"],
            "differences": [], "warnings": [], "review_required": True}


def create_app(settings: Settings | None = None) -> FastAPI:
    s = settings or Settings.from_env()
    install_redaction()
    storage = PrivateStorage(s.storage_dir)
    jobs: dict[str, dict] = {}
    slots = asyncio.Semaphore(s.max_concurrent_jobs)
    require_reviewer = make_reviewer_dependency(s.reviewer_token_hashes)
    upload_limit = RateLimiter(s.upload_rate_limit, s.rate_window_seconds, s.trust_proxy)
    read_limit = RateLimiter(s.read_rate_limit, s.rate_window_seconds, s.trust_proxy)

    async def sweeper():
        while True:
            await asyncio.sleep(s.sweep_interval_seconds)
            n = storage.sweep(s.fallback_cleanup_seconds)
            if n:
                log.info("fallback cleanup removed %d stale upload(s)", n)

    @asynccontextmanager
    async def lifespan(app):
        task = asyncio.create_task(sweeper())
        yield
        task.cancel()

    app = FastAPI(lifespan=lifespan, docs_url="/docs" if s.enable_docs else None,
                  redoc_url=None, openapi_url="/openapi.json" if s.enable_docs else None)
    app.state.jobs, app.state.storage = jobs, storage

    async def process(job_id: str, path):
        jobs[job_id]["state"] = "processing"
        try:
            async with slots:                                   # bounded concurrency
                result = await asyncio.wait_for(run_pipeline(path), s.job_timeout_seconds)
            jobs[job_id].update(state="done", result=result)
        except Exception:                                       # never leak internals
            log.warning("job %s failed", job_id)
            jobs[job_id].update(state="failed", result={"outcome": "unable_to_verify",
                                "reason_codes": ["PROCESSING_ERROR"], "review_required": True})
        finally:
            storage.delete(job_id)                              # cleanup path 1

    @app.post("/api/verifications", status_code=202, dependencies=[Depends(upload_limit)])
    async def create_verification(bg: BackgroundTasks, file: UploadFile = File(...)):
        raw = await read_limited(file, s.max_upload_bytes)
        clean, ext = validate_and_clean_image(raw, s.max_pixels, s.max_dimension)
        job_id, token, token_hash = issue_job()
        path = storage.save(job_id, clean, ext)
        jobs[job_id] = {"state": "queued", "token_hash": token_hash, "created": time.time()}
        bg.add_task(process, job_id, path)
        log.info("job %s accepted (%d bytes)", job_id, len(clean))   # ids and sizes only
        return {"job_id": job_id, "access_token": token}             # token shown once

    @app.get("/api/verifications/{job_id}", dependencies=[Depends(read_limit)])
    async def get_verification(job_id: str, request: Request):
        job = jobs.get(job_id)
        if not job or not check_job_token(request, job["token_hash"]):
            raise NOT_FOUND                                          # no job enumeration
        return {"job_id": job_id, "status": job["state"], **job.get("result", {})}

    @app.get("/api/sources/{source_id}", dependencies=[Depends(read_limit)])
    async def get_source(source_id: str):
        # Read-only public metadata. No write routes exist for sources; imports are CLI-only.
        raise HTTPException(404, "Not found.")   # backend owner: return real source metadata

    @app.get("/api/reviews", dependencies=[Depends(require_reviewer)])
    async def list_reviews():
        return [{"job_id": k, "state": v["state"]} for k, v in jobs.items()
                if v.get("result", {}).get("review_required")]

    @app.post("/api/reviews/{job_id}/decision", dependencies=[Depends(require_reviewer)])
    async def review_decision(job_id: str):
        if job_id not in jobs:
            raise NOT_FOUND
        return {"job_id": job_id, "recorded": True}

    if s.allowed_origins:
        app.add_middleware(CORSMiddleware, allow_origins=list(s.allowed_origins),
                           allow_methods=["GET", "POST"], allow_headers=["Authorization"])
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(BodyLimitMiddleware, max_bytes=s.max_upload_bytes + 1024 * 1024)
    return app




def build() -> FastAPI:
    return create_app()
