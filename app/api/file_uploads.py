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
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_user_auth
from app.schemas.common import ListResponse
from app.schemas.file_upload import FileUploadRead
from app.services.exceptions import BadRequestError, NotFoundError
from app.services.file_upload import FileUploadService, current_person_id

router = APIRouter(
    prefix="/file-uploads",
    tags=["file-uploads"],
)


def _commit(db: Session) -> None:
    db.commit()


def _commit_and_refresh(db: Session, item):
    _commit(db)
    db.refresh(item)
    return item


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
        record = svc.upload_for_actor(
            actor_id=current_person_id(auth),
            content=content,
            filename=file.filename or "unknown",
            content_type=file.content_type or "application/octet-stream",
            category=category,
            entity_type=entity_type,
            entity_id=entity_id,
        )
    except BadRequestError as exc:
        raise _to_http_error(exc) from exc
    _commit_and_refresh(db, record)
    return FileUploadRead.model_validate(record)


@router.get("/{file_id}", response_model=FileUploadRead)
def get_file_upload(
    file_id: UUID,
    auth: dict = Depends(require_user_auth),
    db: Session = Depends(get_db),
) -> FileUploadRead:
    svc = FileUploadService(db)
    record = svc.get_for_actor(file_id, current_person_id(auth))
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
    return FileUploadService(db).list_response_for_actor(
        actor_id=current_person_id(auth),
        category=category,
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
        offset=offset,
    )


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file_upload(
    file_id: UUID,
    auth: dict = Depends(require_user_auth),
    db: Session = Depends(get_db),
) -> None:
    svc = FileUploadService(db)
    try:
        svc.delete_for_actor(file_id, current_person_id(auth))
    except NotFoundError as exc:
        raise _to_http_error(exc) from exc
    _commit(db)
