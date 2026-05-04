from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.common import ListResponse
from app.schemas.rbac import (
    PermissionCreate,
    PermissionRead,
    PermissionUpdate,
    PersonRoleCreate,
    PersonRoleRead,
    PersonRoleUpdate,
    RoleCreate,
    RolePermissionCreate,
    RolePermissionRead,
    RolePermissionUpdate,
    RoleRead,
    RoleUpdate,
)
from app.services import rbac as rbac_service

router = APIRouter(prefix="/rbac", tags=["rbac"])


def _commit(db: Session) -> None:
    db.commit()


def _commit_and_refresh(db: Session, result):
    _commit(db)
    if result is not None:
        db.refresh(result)
    return result


@router.post("/roles", response_model=RoleRead, status_code=status.HTTP_201_CREATED)
def create_role(payload: RoleCreate, db: Session = Depends(get_db)):
    return _commit_and_refresh(db, rbac_service.Roles(db).create(payload))


@router.get("/roles/{role_id}", response_model=RoleRead)
def get_role(role_id: str, db: Session = Depends(get_db)):
    return rbac_service.Roles(db).get(role_id)


@router.get("/roles", response_model=ListResponse[RoleRead])
def list_roles(
    is_active: bool | None = None,
    order_by: str = Query(default="name"),
    order_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return rbac_service.Roles(db).list_response(
        is_active, order_by, order_dir, limit, offset
    )


@router.patch("/roles/{role_id}", response_model=RoleRead)
def update_role(role_id: str, payload: RoleUpdate, db: Session = Depends(get_db)):
    return _commit_and_refresh(db, rbac_service.Roles(db).update(role_id, payload))


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(role_id: str, db: Session = Depends(get_db)):
    rbac_service.Roles(db).delete(role_id)
    _commit(db)


@router.post(
    "/permissions", response_model=PermissionRead, status_code=status.HTTP_201_CREATED
)
def create_permission(payload: PermissionCreate, db: Session = Depends(get_db)):
    return _commit_and_refresh(db, rbac_service.Permissions(db).create(payload))


@router.get("/permissions/{permission_id}", response_model=PermissionRead)
def get_permission(permission_id: str, db: Session = Depends(get_db)):
    return rbac_service.Permissions(db).get(permission_id)


@router.get("/permissions", response_model=ListResponse[PermissionRead])
def list_permissions(
    is_active: bool | None = None,
    order_by: str = Query(default="key"),
    order_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return rbac_service.Permissions(db).list_response(
        is_active, order_by, order_dir, limit, offset
    )


@router.patch("/permissions/{permission_id}", response_model=PermissionRead)
def update_permission(
    permission_id: str, payload: PermissionUpdate, db: Session = Depends(get_db)
):
    return _commit_and_refresh(
        db, rbac_service.Permissions(db).update(permission_id, payload)
    )


@router.delete("/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_permission(permission_id: str, db: Session = Depends(get_db)):
    rbac_service.Permissions(db).delete(permission_id)
    _commit(db)


@router.post(
    "/role-permissions",
    response_model=RolePermissionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_role_permission(
    payload: RolePermissionCreate, db: Session = Depends(get_db)
):
    return _commit_and_refresh(db, rbac_service.RolePermissions(db).create(payload))


@router.get("/role-permissions/{link_id}", response_model=RolePermissionRead)
def get_role_permission(link_id: str, db: Session = Depends(get_db)):
    return rbac_service.RolePermissions(db).get(link_id)


@router.get("/role-permissions", response_model=ListResponse[RolePermissionRead])
def list_role_permissions(
    role_id: str | None = None,
    permission_id: str | None = None,
    order_by: str = Query(default="role_id"),
    order_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return rbac_service.RolePermissions(db).list_response(
        role_id, permission_id, order_by, order_dir, limit, offset
    )


@router.patch("/role-permissions/{link_id}", response_model=RolePermissionRead)
def update_role_permission(
    link_id: str, payload: RolePermissionUpdate, db: Session = Depends(get_db)
):
    return _commit_and_refresh(
        db, rbac_service.RolePermissions(db).update(link_id, payload)
    )


@router.delete("/role-permissions/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role_permission(link_id: str, db: Session = Depends(get_db)):
    rbac_service.RolePermissions(db).delete(link_id)
    _commit(db)


@router.post(
    "/person-roles", response_model=PersonRoleRead, status_code=status.HTTP_201_CREATED
)
def create_person_role(payload: PersonRoleCreate, db: Session = Depends(get_db)):
    return _commit_and_refresh(db, rbac_service.PersonRoles(db).create(payload))


@router.get("/person-roles/{link_id}", response_model=PersonRoleRead)
def get_person_role(link_id: str, db: Session = Depends(get_db)):
    return rbac_service.PersonRoles(db).get(link_id)


@router.get("/person-roles", response_model=ListResponse[PersonRoleRead])
def list_person_roles(
    person_id: str | None = None,
    role_id: str | None = None,
    order_by: str = Query(default="assigned_at"),
    order_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return rbac_service.PersonRoles(db).list_response(
        person_id, role_id, order_by, order_dir, limit, offset
    )


@router.patch("/person-roles/{link_id}", response_model=PersonRoleRead)
def update_person_role(
    link_id: str, payload: PersonRoleUpdate, db: Session = Depends(get_db)
):
    return _commit_and_refresh(
        db, rbac_service.PersonRoles(db).update(link_id, payload)
    )


@router.delete("/person-roles/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_person_role(link_id: str, db: Session = Depends(get_db)):
    rbac_service.PersonRoles(db).delete(link_id)
    _commit(db)
