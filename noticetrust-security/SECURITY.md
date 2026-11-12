# Security notes and known limitations

## What is implemented
Upload validation and re-encoding, 10 MB and decoded-pixel limits, scoped job tokens, protected reviewer endpoints, no public source writes, rate limits, bounded concurrency and timeouts, private storage (dir 0700, files 0600), delete-after-processing plus 1-hour fallback sweep, log redaction, security headers, CI scanning. See `THREAT_MODEL.md` and `tests/test_security.py`.

## Honest limitations (please read before relying on this)
- **Rate limiter and job store are in memory, single process.** Behind several workers or after a restart the limits reset. Use Redis (or the platform's edge rate limiting) for anything beyond a demo.
- **No DDoS protection.** Put the app behind a CDN or WAF (for example Cloudflare) for a real deployment.
- **Reviewer auth is static bearer tokens.** There is no login, expiry, MFA or per-reviewer audit trail yet. Next step is a proper identity provider.
- **Job tokens are bearer secrets.** Anyone holding the token can read that job's result. Send it in the Authorization header, never in a URL.
- **No antivirus scanning.** Re-encoding removes appended payloads, but a decoder bug in Pillow is still possible. Keep Pillow updated (pip-audit runs in CI).
- **Results are not persisted by this module.** Retention of result records (not images) is a backend decision.
- **Deletion is a normal file delete, not secure erase**, and platform backups or snapshots are outside our control.
- **Reverse proxy IP handling:** `NT_TRUST_PROXY=1` is only safe behind exactly one proxy you control.
- This has not had an independent penetration test.

## Reporting
Contact the team lead for the hackathon submission.
