# NoticeTrust threat model (MVP)

**What we protect:** users' uploaded screenshots (may show phone numbers, names, voter details), the integrity of the source corpus, reviewer decisions, and public trust in what NoticeTrust says.

**Who attacks:** anonymous uploaders, people trying to knock the service over during an election period, people trying to make NoticeTrust "approve" a fake notice, and anyone trying to read another user's results.

| # | Threat | Control | Status |
|---|--------|---------|--------|
| 1 | Malicious file disguised as an image (wrong extension, polyglot, appended payload) | Magic-byte check, full decode, re-encode (drops trailing bytes and EXIF/GPS), filename ignored | Done, tested |
| 2 | Oversized upload or chunked flood | 10 MB cap enforced by ASGI middleware (including chunked bodies) and streaming reader | Done, tested |
| 3 | Decompression bomb (small file, huge pixels) | Pixel and per-side limits checked from the header before decoding | Done, tested |
| 4 | Reading another user's job or guessing job IDs | Random 256-bit per-job token, only its hash is stored, identical 404 for missing and not-yours | Done, tested |
| 5 | Unauthorised access to the reviewer queue or decisions | Bearer token checked in constant time against hashed allowlist; no reviewers configured means nobody gets in | Done, tested |
| 6 | Tampering with the source corpus (poisoned "official" sources) | No public write routes for sources; corpus import is a CLI run by the team only | Done (by design), tested |
| 7 | Resource exhaustion (many uploads, slow OCR) | Per-IP rate limits, concurrency semaphore, per-job timeout | Done, in-memory only |
| 8 | Leftover sensitive images | Delete in `finally` after processing, plus sweeper for anything older than 1 hour | Done, both paths tested |
| 9 | Secrets or tokens in logs or git | Redaction filter, logs hold job IDs and sizes only, `.gitignore`, gitleaks in CI | Done |
| 10 | Prompt injection through text inside the image (OCR text says "ignore previous instructions") | OCR text is data only. Results use reviewed templates and deterministic field comparison. If any LLM is added, never give it OCR text as instructions | Design rule, backend must follow |
| 11 | Misuse of a "match" as an official endorsement | Result copy says visible text matches, not "authentic". No uncalibrated authenticity percentages | Frontend/backend, per PRD |
| 12 | Browser attacks on the API (clickjacking, sniffing, caching of results) | nosniff, DENY framing, no-store, strict CSP, explicit CORS origins (no wildcard) | Done, tested |
| 13 | Vulnerable dependencies | pip-audit and bandit in CI | Done |
