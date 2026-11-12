"""Request body cap (works for chunked uploads too) and security headers."""
from starlette.responses import JSONResponse


class _TooLarge(Exception):
    pass


class BodyLimitMiddleware:
    def __init__(self, app, max_bytes: int):
        self.app, self.max = app, max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        cl = dict(scope["headers"]).get(b"content-length")
        if cl and cl.isdigit() and int(cl) > self.max:
            return await self._reject(scope, receive, send)
        seen, started, exceeded = 0, False, False

        async def limited_receive():
            nonlocal seen, exceeded
            msg = await receive()
            if msg["type"] == "http.request":
                seen += len(msg.get("body", b""))
                if seen > self.max:
                    exceeded = True
                    raise _TooLarge()
            return msg

        async def tracking_send(m):
            nonlocal started
            if exceeded and not started:
                # The app turned our abort into some other error (e.g. 400 from the form parser).
                # Report it honestly as 413 and drop the app's own response.
                if m["type"] == "http.response.start":
                    started = True
                    await send({"type": "http.response.start", "status": 413,
                                "headers": [(b"content-type", b"application/json")]})
                    await send({"type": "http.response.body", "body": b'{"detail":"Request too large."}'})
                return
            if exceeded and started:
                return
            if m["type"] == "http.response.start":
                started = True
            await send(m)

        try:
            await self.app(scope, limited_receive, tracking_send)
        except _TooLarge:
            if not started:
                await self._reject(scope, receive, send)

    async def _reject(self, scope, receive, send):
        await JSONResponse({"detail": "Request too large."}, status_code=413)(scope, receive, send)


class SecurityHeadersMiddleware:
    HEADERS = [
        (b"x-content-type-options", b"nosniff"),
        (b"x-frame-options", b"DENY"),
        (b"referrer-policy", b"no-referrer"),
        (b"cache-control", b"no-store"),
        (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'"),
        (b"strict-transport-security", b"max-age=31536000; includeSubDomains"),
        (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
    ]

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def send_with_headers(m):
            if m["type"] == "http.response.start":
                m["headers"] = list(m.get("headers", [])) + self.HEADERS
            await send(m)

        await self.app(scope, receive, send_with_headers)
