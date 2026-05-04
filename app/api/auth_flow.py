from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.auth import MFAMethodRead
from app.schemas.auth_flow import (
    AvatarUploadResponse,
    ErrorResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    LogoutResponse,
    MeResponse,
    MeUpdateRequest,
    MfaConfirmRequest,
    MfaSetupRequest,
    MfaSetupResponse,
    MfaVerifyRequest,
    PasswordChangeRequest,
    PasswordChangeResponse,
    RefreshRequest,
    ResetPasswordRequest,
    ResetPasswordResponse,
    SessionListResponse,
    SessionRevokeResponse,
    TokenResponse,
)
from app.services import auth_flow as auth_flow_service
from app.services.auth_dependencies import require_user_auth
from app.services.auth_flow import (
    request_password_reset,
    reset_password,
)
from app.services.email import send_password_reset_email

router = APIRouter(prefix="/auth", tags=["auth"])


def _commit(db: Session) -> None:
    db.commit()


def _commit_and_refresh(db: Session, item):
    _commit(db)
    db.refresh(item)
    return item


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    responses={
        428: {
            "model": ErrorResponse,
            "description": "Password reset required",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "code": "PASSWORD_RESET_REQUIRED",
                            "message": "Password reset required",
                        }
                    }
                }
            },
        }
    },
)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    try:
        response = auth_flow_service.auth_flow.login_response(
            db, payload.username, payload.password, request, payload.provider
        )
    except HTTPException:
        _commit(db)
        raise
    _commit(db)
    return response


@router.post(
    "/mfa/setup",
    response_model=MfaSetupResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
)
def mfa_setup(
    payload: MfaSetupRequest,
    auth: dict = Depends(require_user_auth),
    db: Session = Depends(get_db),
):
    if str(payload.person_id) != auth["person_id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    response = auth_flow_service.auth_flow.mfa_setup(
        db, auth["person_id"], payload.label
    )
    _commit(db)
    return response


@router.post(
    "/mfa/confirm",
    response_model=MFAMethodRead,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
def mfa_confirm(
    payload: MfaConfirmRequest,
    auth: dict = Depends(require_user_auth),
    db: Session = Depends(get_db),
):
    method = auth_flow_service.auth_flow.mfa_confirm(
        db, str(payload.method_id), payload.code, auth["person_id"]
    )
    return _commit_and_refresh(db, method)


@router.post(
    "/mfa/verify",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
def mfa_verify(
    payload: MfaVerifyRequest, request: Request, db: Session = Depends(get_db)
):
    response = auth_flow_service.auth_flow.mfa_verify_response(
        db, payload.mfa_token, payload.code, request
    )
    _commit(db)
    return response


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse},
    },
)
def refresh(payload: RefreshRequest, request: Request, db: Session = Depends(get_db)):
    try:
        response = auth_flow_service.auth_flow.refresh_response(
            db, payload.refresh_token, request
        )
    except HTTPException:
        _commit(db)
        raise
    _commit(db)
    return response


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse},
    },
)
def logout(payload: LogoutRequest, request: Request, db: Session = Depends(get_db)):
    response = auth_flow_service.auth_flow.logout_response(
        db, payload.refresh_token, request
    )
    _commit(db)
    return response


@router.get(
    "/me",
    response_model=MeResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse},
    },
)
def get_me(
    auth: dict = Depends(require_user_auth),
    db: Session = Depends(get_db),
):
    return auth_flow_service.auth_flow.me_response(db, auth)


@router.patch(
    "/me",
    response_model=MeResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse},
    },
)
def update_me(
    payload: MeUpdateRequest,
    auth: dict = Depends(require_user_auth),
    db: Session = Depends(get_db),
):
    response = auth_flow_service.auth_flow.update_me_response(db, auth, payload)
    _commit(db)
    return response


@router.post(
    "/me/avatar",
    response_model=AvatarUploadResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
    },
)
async def upload_avatar(
    file: UploadFile,
    auth: dict = Depends(require_user_auth),
    db: Session = Depends(get_db),
):
    response = await auth_flow_service.auth_flow.upload_avatar_response(db, auth, file)
    _commit(db)
    return response


@router.delete(
    "/me/avatar",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"model": ErrorResponse},
    },
)
def delete_avatar(
    auth: dict = Depends(require_user_auth),
    db: Session = Depends(get_db),
):
    auth_flow_service.auth_flow.delete_avatar(db, auth)
    _commit(db)


@router.get(
    "/me/sessions",
    response_model=SessionListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse},
    },
)
def list_sessions(
    auth: dict = Depends(require_user_auth),
    db: Session = Depends(get_db),
):
    return auth_flow_service.auth_flow.list_sessions_response(db, auth)


@router.delete(
    "/me/sessions/{session_id}",
    response_model=SessionRevokeResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
def revoke_session(
    session_id: str,
    auth: dict = Depends(require_user_auth),
    db: Session = Depends(get_db),
):
    response = auth_flow_service.auth_flow.revoke_session_response(db, auth, session_id)
    _commit(db)
    return response


@router.delete(
    "/me/sessions",
    response_model=SessionRevokeResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse},
    },
)
def revoke_all_other_sessions(
    auth: dict = Depends(require_user_auth),
    db: Session = Depends(get_db),
):
    response = auth_flow_service.auth_flow.revoke_all_other_sessions_response(db, auth)
    _commit(db)
    return response


@router.post(
    "/me/password",
    response_model=PasswordChangeResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
def change_password(
    payload: PasswordChangeRequest,
    auth: dict = Depends(require_user_auth),
    db: Session = Depends(get_db),
):
    response = auth_flow_service.auth_flow.change_password_response(db, auth, payload)
    _commit(db)
    return response


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    status_code=status.HTTP_200_OK,
)
def forgot_password(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    """
    Request a password reset email.
    Always returns success to prevent email enumeration.
    """
    result = request_password_reset(db, payload.email)

    if result:
        send_password_reset_email(
            db=db,
            to_email=result["email"],
            reset_token=result["token"],
            person_name=result["person_name"],
        )

    return ForgotPasswordResponse()


@router.post(
    "/reset-password",
    response_model=ResetPasswordResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
def reset_password_endpoint(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    """
    Reset password using the token from forgot-password email.
    """
    reset_at = reset_password(db, payload.token, payload.new_password)
    _commit(db)
    return ResetPasswordResponse(reset_at=reset_at)
