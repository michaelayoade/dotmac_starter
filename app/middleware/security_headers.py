"""Security headers middleware.

Adds OWASP-recommended HTTP security headers to every response.
Generates a per-request CSP nonce stored on request.state.csp_nonce so
Jinja2 templates can attach it to any remaining inline <script> tags.
"""
from __future__ import annotations

import base64
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Injects security headers into every HTTP response."""

    async def dispatch(self, request: Request, call_next: object) -> Response:
        # Generate a cryptographically random per-request nonce.
        # Stored on request.state so templates can use it:
        #   <script nonce="{{ request.state.csp_nonce }}">...</script>
        nonce = base64.b64encode(secrets.token_bytes(16)).decode("ascii")
        request.state.csp_nonce = nonce

        response: Response = await call_next(request)  # type: ignore[call-arg]

        # Prevent MIME-sniffing
        response.headers.setdefault("X-Content-Type-Options", "nosniff")

        # Clickjacking protection
        response.headers.setdefault("X-Frame-Options", "DENY")

        # XSS filter (legacy browsers)
        response.headers.setdefault("X-XSS-Protection", "1; mode=block")

        # Control referrer leakage
        response.headers.setdefault(
            "Referrer-Policy", "strict-origin-when-cross-origin"
        )

        # Restrict browser features
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), payment=()",
        )

        # Content Security Policy — nonce-based; no unsafe-inline for scripts.
        # 'unsafe-eval' is retained because Alpine.js v3 uses new Function()
        # internally to evaluate x-data/x-on expressions.  Removing it would
        # require switching to the @alpinejs/csp pre-compiled build.
        # style-src retains 'unsafe-inline' because Tailwind CDN injects
        # <style> blocks at runtime and base.html has a <style> block.
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            f"script-src 'self' 'nonce-{nonce}' 'unsafe-eval' "
            "https://cdn.tailwindcss.com https://unpkg.com https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )

        # HSTS — only set when behind TLS (proxy sets X-Forwarded-Proto)
        forwarded_proto = request.headers.get("x-forwarded-proto", "")
        if forwarded_proto == "https":
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )

        return response
