"""Scoped job access: random bearer token per job; only its hash is stored."""
import hashlib
import hmac
import secrets
import uuid


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_job() -> tuple[str, str, str]:
    """Return (job_id, plaintext_token, token_hash). Show the token to the user ONCE."""
    job_id = uuid.uuid4().hex
    token = secrets.token_urlsafe(32)
    return job_id, token, hash_token(token)


def token_matches(presented: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_token(presented), stored_hash)
