from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_user_auth
from app.models.rbac import PersonRole, Role
from app.schemas.common import ListResponse
from app.schemas.file_upload import FileUploadRead
from app.services.common import coerce_uuid
from app.services.exceptions import BadRequestError, NotFoundError
from app.services.file_upload import FileUploadService

router = APIRouter(
    prefix="/file-uploads",
    tags=["file-uploads"],
)


def _is_admin(db: Session, person_id: UUID) -> bool:
    return (
        db.scalars(
            select(PersonRole)
            .join(Role, PersonRole.role_id == Role.id)
            .where(PersonRole.person_id == person_id)
            .where(Role.name == "admin")
            .where(Role.is_active.is_(True))
            .limit(1)
        ).first()
        is not None
    )


def _current_person_id(auth: dict) -> UUID:
    person_id = coerce_uuid(auth["person_id"])
    if person_id is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return person_id


def _to_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


@router.post("", response_model=FileUploadRead, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    category: str = Form(default="document"),
    entity_type: str | None = Form(default=None),
    entity_id: str | None = Form(default=None),
    auth: dict = Depends(require_user_auth),
    db: Session = Depends(get_db),
) -> FileUploadRead:
    content = await file.read()
    svc = FileUploadService(db)
    try:
        record = svc.upload(
            content=content,
            filename=file.filename or "unknown",
            content_type=file.content_type or "application/octet-stream",
            uploaded_by=_current_person_id(auth),
            category=category,
            entity_type=entity_type,
            entity_id=entity_id,
        )
    except BadRequestError as exc:
        raise _to_http_error(exc) from exc
    db.commit()
    db.refresh(record)
    return FileUploadRead.model_validate(record)


@router.get("/{file_id}", response_model=FileUploadRead)
def get_file_upload(
    file_id: UUID,
    auth: dict = Depends(require_user_auth),
    db: Session = Depends(get_db),
) -> FileUploadRead:
    person_id = _current_person_id(auth)
    svc = FileUploadService(db)
    record = svc.get_by_id(file_id)
    if (
        not record
        or not record.is_active
        or (not _is_admin(db, person_id) and record.uploaded_by != person_id)
    ):
        raise HTTPException(status_code=404, detail="File upload not found")
    return FileUploadRead.model_validate(record)


@router.get("", response_model=ListResponse[FileUploadRead])
def list_file_uploads(
    category: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    auth: dict = Depends(require_user_auth),
    db: Session = Depends(get_db),
) -> ListResponse[FileUploadRead]:
    person_id = _current_person_id(auth)
    uploaded_by = None if _is_admin(db, person_id) else person_id
    svc = FileUploadService(db)
    items = svc.list_uploads(
        uploaded_by=uploaded_by,
        category=category,
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
        offset=offset,
    )
    total = svc.count(
        uploaded_by=uploaded_by,
        category=category,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    return ListResponse(
        items=[FileUploadRead.model_validate(i) for i in items],
        count=len(items),
        limit=limit,
        offset=offset,
        total=total,
    )


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file_upload(
    file_id: UUID,
    auth: dict = Depends(require_user_auth),
    db: Session = Depends(get_db),
) -> None:
    person_id = _current_person_id(auth)
    svc = FileUploadService(db)
    record = svc.get_by_id(file_id)
    if (
        not record
        or not record.is_active
        or (not _is_admin(db, person_id) and record.uploaded_by != person_id)
    ):
        raise HTTPException(status_code=404, detail="File upload not found")
    try:
        svc.delete(file_id)
    except NotFoundError as exc:
        raise _to_http_error(exc) from exc
    db.commit()
