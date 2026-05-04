from app.schemas.rbac import (
    PermissionCreate,
    PermissionUpdate,
    RoleCreate,
    RolePermissionCreate,
    RoleUpdate,
)
from app.services import rbac as rbac_service


def test_role_permission_link_flow(db_session):
    roles = rbac_service.Roles(db_session)
    permissions = rbac_service.Permissions(db_session)
    role_permissions = rbac_service.RolePermissions(db_session)
    role = roles.create(RoleCreate(name="Support"))
    permission = permissions.create(
        PermissionCreate(key="people:read", description="Read People")
    )
    link = role_permissions.create(
        RolePermissionCreate(role_id=role.id, permission_id=permission.id),
    )
    items = role_permissions.list(
        role_id=role.id,
        permission_id=None,
        order_by="role_id",
        order_dir="desc",
        limit=10,
        offset=0,
    )
    assert items[0].id == link.id


def test_role_permission_soft_delete_filters(db_session):
    roles = rbac_service.Roles(db_session)
    role = roles.create(RoleCreate(name="Settings"))
    roles.update(str(role.id), RoleUpdate(name="Settings Ops"))
    roles.delete(str(role.id))
    active = roles.list(
        is_active=None,
        order_by="created_at",
        order_dir="desc",
        limit=10,
        offset=0,
    )
    inactive = roles.list(
        is_active=False,
        order_by="created_at",
        order_dir="desc",
        limit=10,
        offset=0,
    )
    assert role not in active
    assert any(item.id == role.id for item in inactive)


def test_permission_update(db_session):
    permissions = rbac_service.Permissions(db_session)
    permission = permissions.create(
        PermissionCreate(key="settings:write", description="Settings Write")
    )
    updated = permissions.update(
        str(permission.id),
        PermissionUpdate(description="Settings Write Access"),
    )
    assert updated.description == "Settings Write Access"
