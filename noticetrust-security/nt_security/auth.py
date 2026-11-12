"""Bearer-token helpers: job access (per-user) and reviewer access (protected)."""
import hmac

from fastapi import HTTPException, Request

from .tokens import hash_token, token_matches


def bearer(request: Request) -> str | None:
    scheme, _, value = request.headers.get("authorization", "").partition(" ")
    return value.strip() if scheme.lower() == "bearer" and value.strip() else None


def make_reviewer_dependency(allowed_hashes: tuple):
    def require_reviewer(request: Request):
        tok = bearer(request)
        ok = False
        if tok:
            h = hash_token(tok)
            for allowed in allowed_hashes:         # compare against all, constant time each
                ok |= hmac.compare_digest(h, allowed)
        if not ok:
            raise HTTPException(401, "Reviewer authentication required.",
                                headers={"WWW-Authenticate": "Bearer"})
    return require_reviewer


def check_job_token(request: Request, stored_hash: str | None) -> bool:
    tok = bearer(request)
    return bool(tok and stored_hash and token_matches(tok, stored_hash))
