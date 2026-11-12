# NoticeTrust security module (Workstream C)

Drop-in controls for the FastAPI backend, plus tests, threat model and CI.

## Integrate (5 minutes)
1. Copy `nt_security/` into the backend and `pip install -r requirements.txt`.
2. In your routes, copy the guards from `app.py`: `read_limited` + `validate_and_clean_image` on upload, `issue_job` for the token, `check_job_token` on reads, `Depends(require_reviewer)` on `/api/reviews*`, `storage.delete(job_id)` in a `finally`.
3. Add `BodyLimitMiddleware` and `SecurityHeadersMiddleware` (see end of `create_app`).
4. Set env vars from `.env.example`. Make a reviewer token: `python -m scripts.make_reviewer_token`.

## Run
    pip install -r requirements-dev.txt
    pytest -q
    NT_ENABLE_DOCS=1 uvicorn app:build --factory --port 8000

## Demo checks
    curl -i -F "file=@fake.png;type=image/png" localhost:8000/api/verifications    # 415 for non-images
    curl -i localhost:8000/api/reviews                                              # 401
