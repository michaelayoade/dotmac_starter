from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.auth import (
    ApiKeyCreate,
    ApiKeyGenerateRequest,
    ApiKeyGenerateResponse,
    ApiKeyRead,
    ApiKeyUpdate,
    MFAMethodCreate,
    MFAMethodRead,
    MFAMethodUpdate,
    SessionCreate,
    SessionRead,
    SessionUpdate,
    UserCredentialCreate,
    UserCredentialRead,
    UserCredentialUpdate,
)
from app.schemas.common import ListResponse
from app.services import auth as auth_service
from app.services.exceptions import (
    ConflictError,
    NotFoundError,
    RateLimitError,
    ServiceUnavailableError,
)

router = APIRouter()


def _to_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ConflictError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, RateLimitError):
        return HTTPException(status_code=429, detail=str(exc))
    if isinstance(exc, ServiceUnavailableError):
        return HTTPException(status_code=503, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


def _commit(db: Session) -> None:
    db.commit()


def _commit_and_refresh(db: Session, result):
    _commit(db)
    if result is not None:
        db.refresh(result)
    return result


@router.post(
    "/user-credentials",
    response_model=UserCredentialRead,
    status_code=status.HTTP_201_CREATED,
    tags=["user-credentials"],
)
def create_user_credential(
    payload: UserCredentialCreate, db: Session = Depends(get_db)
):
    try:
        return _commit_and_refresh(db, auth_service.UserCredentials(db).create(payload))
    except (NotFoundError, ServiceUnavailableError) as exc:
        raise _to_http_error(exc) from exc


@router.get(
    "/user-credentials/{credential_id}",
    response_model=UserCredentialRead,
    tags=["user-credentials"],
)
def get_user_credential(credential_id: str, db: Session = Depends(get_db)):
    try:
        return auth_service.UserCredentials(db).get(credential_id)
    except NotFoundError as exc:
        raise _to_http_error(exc) from exc


@router.get(
    "/user-credentials",
    response_model=ListResponse[UserCredentialRead],
    tags=["user-credentials"],
)
def list_user_credentials(
    person_id: str | None = None,
    provider: str | None = None,
    is_active: bool | None = None,
    order_by: str = Query(default="created_at"),
    order_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return auth_service.UserCredentials(db).list_response(
        person_id, provider, is_active, order_by, order_dir, limit, offset
    )


@router.patch(
    "/user-credentials/{credential_id}",
    response_model=UserCredentialRead,
    tags=["user-credentials"],
)
def update_user_credential(
    credential_id: str, payload: UserCredentialUpdate, db: Session = Depends(get_db)
):
    try:
        return _commit_and_refresh(
            db, auth_service.UserCredentials(db).update(credential_id, payload)
        )
    except NotFoundError as exc:
        raise _to_http_error(exc) from exc


@router.delete(
    "/user-credentials/{credential_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["user-credentials"],
)
def delete_user_credential(credential_id: str, db: Session = Depends(get_db)):
    try:
        auth_service.UserCredentials(db).delete(credential_id)
    except NotFoundError as exc:
        raise _to_http_error(exc) from exc
    _commit(db)


@router.post(
    "/mfa-methods",
    response_model=MFAMethodRead,
    status_code=status.HTTP_201_CREATED,
    tags=["mfa-methods"],
)
def create_mfa_method(payload: MFAMethodCreate, db: Session = Depends(get_db)):
    try:
        return _commit_and_refresh(db, auth_service.MFAMethods(db).create(payload))
    except (NotFoundError, ConflictError) as exc:
        raise _to_http_error(exc) from exc


@router.get(
    "/mfa-methods/{method_id}",
    response_model=MFAMethodRead,
    tags=["mfa-methods"],
)
def get_mfa_method(method_id: str, db: Session = Depends(get_db)):
    try:
        return auth_service.MFAMethods(db).get(method_id)
    except NotFoundError as exc:
        raise _to_http_error(exc) from exc


@router.get(
    "/mfa-methods",
    response_model=ListResponse[MFAMethodRead],
    tags=["mfa-methods"],
)
def list_mfa_methods(
    person_id: str | None = None,
    method_type: str | None = None,
    is_primary: bool | None = None,
    enabled: bool | None = None,
    is_active: bool | None = None,
    order_by: str = Query(default="created_at"),
    order_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return auth_service.MFAMethods(db).list_response(
        person_id,
        method_type,
        is_primary,
        enabled,
        is_active,
        order_by,
        order_dir,
        limit,
        offset,
    )


@router.patch(
    "/mfa-methods/{method_id}",
    response_model=MFAMethodRead,
    tags=["mfa-methods"],
)
def update_mfa_method(
    method_id: str, payload: MFAMethodUpdate, db: Session = Depends(get_db)
):
    try:
        return _commit_and_refresh(
            db, auth_service.MFAMethods(db).update(method_id, payload)
        )
    except (NotFoundError, ConflictError) as exc:
        raise _to_http_error(exc) from exc


@router.delete(
    "/mfa-methods/{method_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["mfa-methods"],
)
def delete_mfa_method(method_id: str, db: Session = Depends(get_db)):
    try:
        auth_service.MFAMethods(db).delete(method_id)
    except NotFoundError as exc:
        raise _to_http_error(exc) from exc
    _commit(db)


@router.post(
    "/sessions",
    response_model=SessionRead,
    status_code=status.HTTP_201_CREATED,
    tags=["sessions"],
)
def create_session(payload: SessionCreate, db: Session = Depends(get_db)):
    try:
        return _commit_and_refresh(db, auth_service.Sessions(db).create(payload))
    except NotFoundError as exc:
        raise _to_http_error(exc) from exc


@router.get(
    "/sessions/{session_id}",
    response_model=SessionRead,
    tags=["sessions"],
)
def get_session(session_id: str, db: Session = Depends(get_db)):
    try:
        return auth_service.Sessions(db).get(session_id)
    except NotFoundError as exc:
        raise _to_http_error(exc) from exc


@router.get(
    "/sessions",
    response_model=ListResponse[SessionRead],
    tags=["sessions"],
)
def list_sessions(
    person_id: str | None = None,
    status: str | None = None,
    order_by: str = Query(default="created_at"),
    order_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return auth_service.Sessions(db).list_response(
        person_id, status, order_by, order_dir, limit, offset
    )


@router.patch(
    "/sessions/{session_id}",
    response_model=SessionRead,
    tags=["sessions"],
)
def update_session(
    session_id: str, payload: SessionUpdate, db: Session = Depends(get_db)
):
    try:
        return _commit_and_refresh(
            db, auth_service.Sessions(db).update(session_id, payload)
        )
    except NotFoundError as exc:
        raise _to_http_error(exc) from exc


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["sessions"],
)
def delete_session(session_id: str, db: Session = Depends(get_db)):
    try:
        auth_service.Sessions(db).delete(session_id)
    except NotFoundError as exc:
        raise _to_http_error(exc) from exc
    _commit(db)


@router.post(
    "/api-keys",
    response_model=ApiKeyRead,
    status_code=status.HTTP_201_CREATED,
    tags=["api-keys"],
)
def create_api_key(payload: ApiKeyCreate, db: Session = Depends(get_db)):
    try:
        return _commit_and_refresh(db, auth_service.ApiKeys(db).create(payload))
    except (NotFoundError, ServiceUnavailableError) as exc:
        raise _to_http_error(exc) from exc


@router.post(
    "/api-keys/generate",
    response_model=ApiKeyGenerateResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["api-keys"],
)
def generate_api_key(
    payload: ApiKeyGenerateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        result = auth_service.ApiKeys(db).generate_with_rate_limit(payload, request)
    except (
        NotFoundError,
        RateLimitError,
        ServiceUnavailableError,
    ) as exc:
        raise _to_http_error(exc) from exc
    _commit(db)
    db.refresh(result["api_key"])
    return result


@router.get(
    "/api-keys/{key_id}",
    response_model=ApiKeyRead,
    tags=["api-keys"],
)
def get_api_key(key_id: str, db: Session = Depends(get_db)):
    try:
        return auth_service.ApiKeys(db).get(key_id)
    except NotFoundError as exc:
        raise _to_http_error(exc) from exc


@router.get(
    "/api-keys",
    response_model=ListResponse[ApiKeyRead],
    tags=["api-keys"],
)
def list_api_keys(
    person_id: str | None = None,
    is_active: bool | None = None,
    order_by: str = Query(default="created_at"),
    order_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return auth_service.ApiKeys(db).list_response(
        person_id, is_active, order_by, order_dir, limit, offset
    )


@router.patch(
    "/api-keys/{key_id}",
    response_model=ApiKeyRead,
    tags=["api-keys"],
)
def update_api_key(key_id: str, payload: ApiKeyUpdate, db: Session = Depends(get_db)):
    try:
        return _commit_and_refresh(db, auth_service.ApiKeys(db).update(key_id, payload))
    except (NotFoundError, ServiceUnavailableError) as exc:
        raise _to_http_error(exc) from exc


@router.delete(
    "/api-keys/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["api-keys"],
)
def delete_api_key(key_id: str, db: Session = Depends(get_db)):
    try:
        auth_service.ApiKeys(db).revoke(key_id)
    except NotFoundError as exc:
        raise _to_http_error(exc) from exc
    _commit(db)
