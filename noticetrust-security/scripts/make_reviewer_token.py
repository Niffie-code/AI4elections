"""Generate a reviewer token. Give the token to the reviewer; put the HASH in NT_REVIEWER_TOKEN_HASHES."""
import secrets
from nt_security.tokens import hash_token

t = secrets.token_urlsafe(32)
print("TOKEN (give to reviewer, keep out of git):", t)
print("HASH  (goes in NT_REVIEWER_TOKEN_HASHES):  ", hash_token(t))
