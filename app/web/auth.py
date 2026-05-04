"""Web authentication routes — login and logout pages."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.auth import Session as AuthSession
from app.models.auth import SessionStatus
from app.services.auth_flow import decode_access_token, session_token_hash_candidates
from app.services.branding_context import load_branding_context
from app.services.common import coerce_uuid
from app.templates import templates

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["web-auth"])


def _commit(db: Session) -> None:
    db.commit()


def _is_secure_request(request: Request) -> bool:
    """Return True if request is over HTTPS."""
    proto = request.headers.get("x-forwarded-proto", "")
    return proto == "https" or request.url.scheme == "https"


@router.get("/login", response_class=HTMLResponse)
def login_page(
    request: Request,
    next: str = "/admin",
    db: Session = Depends(get_db),
) -> HTMLResponse:
    branding = load_branding_context(db)
    return templates.TemplateResponse(
        "admin/login.html",
        {
            "request": request,
            "title": "Login",
            "next_url": next,
            "brand": branding["brand"],
            "org_branding": branding["org_branding"],
        },
    )


def _login_error(
    request: Request, db: Session, message: str, next_url: str
) -> HTMLResponse:
    branding = load_branding_context(db)
    return templates.TemplateResponse(
        "admin/login.html",
        {
            "request": request,
            "title": "Login",
            "error": message,
            "next_url": next_url,
            "brand": branding["brand"],
            "org_branding": branding["org_branding"],
        },
    )


def _safe_next_url(url: str) -> str:
    if url.startswith("/") and not url.startswith("//") and "://" not in url:
        return url
    return "/admin"


@router.post("/login", response_model=None)
async def login_submit(
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    form = await request.form()
    username = str(form.get("username", "")).strip()
    password = str(form.get("password", ""))
    next_url = _safe_next_url(str(form.get("next", "/admin")))

    if not username or not password:
        return _login_error(request, db, "Username and password are required", next_url)

    from app.services.auth_flow import AuthFlow

    try:
        result = AuthFlow.login(db, username, password, request, None)
    except HTTPException:
        return _login_error(request, db, "Invalid username or password", next_url)

    if result.get("mfa_required"):
        return _login_error(
            request, db, "MFA is not yet supported in web login", next_url
        )

    access_token = result.get("access_token", "")
    refresh_token = result.get("refresh_token", "")

    if not access_token:
        return _login_error(request, db, "Login failed", next_url)

    is_secure = _is_secure_request(request)
    response = RedirectResponse(url=next_url, status_code=302)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=is_secure,
        samesite="lax",
        path="/",
        max_age=3600,
    )
    if refresh_token:
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=is_secure,
            samesite="lax",
            path="/",
            max_age=30 * 24 * 3600,
        )
    return response


@router.get("/logout")
def logout(request: Request, db: Session = Depends(get_db)) -> RedirectResponse:
    access_token = request.cookies.get("access_token")
    refresh_token = request.cookies.get("refresh_token")
    try:
        session = None
        if access_token:
            payload = decode_access_token(db, access_token)
            session_id = payload.get("session_id")
            if session_id:
                session = db.get(AuthSession, coerce_uuid(str(session_id)))
        if session is None and refresh_token:
            session = db.scalars(
                select(AuthSession)
                .where(
                    AuthSession.token_hash.in_(
                        session_token_hash_candidates(refresh_token, db)
                    )
                )
                .where(AuthSession.revoked_at.is_(None))
                .limit(1)
            ).first()
        if session is not None and session.revoked_at is None:
            session.status = SessionStatus.revoked
            session.revoked_at = datetime.now(UTC)
            _commit(db)
    except Exception:
        logger.exception("Failed to revoke web session during logout")
        db.rollback()

    response = RedirectResponse(url="/admin/login", status_code=302)
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return response
