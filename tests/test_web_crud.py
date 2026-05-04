"""Tests for web CRUD admin pages."""

import os
from datetime import UTC, datetime, timedelta

from jose import jwt


def _create_access_token(
    person_id: str, session_id: str, roles: list[str] | None = None
) -> str:
    secret = os.getenv("JWT_SECRET", "test-secret")
    algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=15)
    return jwt.encode(
        {
            "sub": person_id,
            "session_id": session_id,
            "roles": roles or [],
            "scopes": [],
            "typ": "access",
            "exp": int(expire.timestamp()),
            "iat": int(now.timestamp()),
        },
        secret,
        algorithm=algorithm,
    )


class TestWebPeople:
    def test_home_does_not_expose_people(self, client, person):
        response = client.get("/")
        assert response.status_code == 200
        assert person.email.encode() not in response.content

    def test_list_requires_auth(self, client):
        response = client.get("/admin/people", follow_redirects=False)
        assert response.status_code == 302

    def test_list_with_auth(self, client, person, auth_session, auth_token):
        response = client.get(
            "/admin/people",
            cookies={"access_token": auth_token},
        )
        assert response.status_code == 200
        assert b"People" in response.content

    def test_list_forbidden_without_admin_role(self, client, person, auth_session):
        token = _create_access_token(str(person.id), str(auth_session.id), roles=[])
        response = client.get(
            "/admin/people",
            cookies={"access_token": token},
        )
        assert response.status_code == 403

    def test_create_page(self, client, person, auth_session, auth_token):
        response = client.get(
            "/admin/people/create",
            cookies={"access_token": auth_token},
        )
        assert response.status_code == 200

    def test_detail_page(self, client, person, auth_session, auth_token):
        response = client.get(
            f"/admin/people/{person.id}",
            cookies={"access_token": auth_token},
        )
        assert response.status_code == 200
        assert person.first_name.encode() in response.content


class TestWebRoles:
    def test_list(self, client, person, auth_session, auth_token):
        response = client.get(
            "/admin/roles",
            cookies={"access_token": auth_token},
        )
        assert response.status_code == 200

    def test_create_page(self, client, person, auth_session, auth_token):
        response = client.get(
            "/admin/roles/create",
            cookies={"access_token": auth_token},
        )
        assert response.status_code == 200


class TestWebPermissions:
    def test_list(self, client, person, auth_session, auth_token):
        response = client.get(
            "/admin/permissions",
            cookies={"access_token": auth_token},
        )
        assert response.status_code == 200

    def test_create_page(self, client, person, auth_session, auth_token):
        response = client.get(
            "/admin/permissions/create",
            cookies={"access_token": auth_token},
        )
        assert response.status_code == 200


class TestWebSettings:
    def test_list(self, client, person, auth_session, auth_token):
        response = client.get(
            "/admin/settings",
            cookies={"access_token": auth_token},
        )
        assert response.status_code == 200

    def test_branding_requires_auth(self, client):
        response = client.get("/settings/branding", follow_redirects=False)
        assert response.status_code == 302

    def test_branding_with_auth(self, client, person, auth_session, auth_token):
        response = client.get(
            "/settings/branding",
            cookies={"access_token": auth_token},
        )
        assert response.status_code == 200


class TestWebScheduler:
    def test_list(self, client, person, auth_session, auth_token):
        response = client.get(
            "/admin/scheduler",
            cookies={"access_token": auth_token},
        )
        assert response.status_code == 200

    def test_create_page(self, client, person, auth_session, auth_token):
        response = client.get(
            "/admin/scheduler/create",
            cookies={"access_token": auth_token},
        )
        assert response.status_code == 200


class TestWebAudit:
    def test_list(self, client, person, auth_session, auth_token):
        response = client.get(
            "/admin/audit",
            cookies={"access_token": auth_token},
        )
        assert response.status_code == 200

    def test_detail(self, client, person, auth_session, auth_token, audit_event):
        response = client.get(
            f"/admin/audit/{audit_event.id}",
            cookies={"access_token": auth_token},
        )
        assert response.status_code == 200


class TestWebNotifications:
    def test_list(self, client, person, auth_session, auth_token):
        response = client.get(
            "/admin/notifications",
            cookies={"access_token": auth_token},
        )
        assert response.status_code == 200


class TestWebFileUploads:
    def test_list(self, client, person, auth_session, auth_token):
        response = client.get(
            "/admin/file-uploads",
            cookies={"access_token": auth_token},
        )
        assert response.status_code == 200

    def test_upload_page(self, client, person, auth_session, auth_token):
        response = client.get(
            "/admin/file-uploads/upload",
            cookies={"access_token": auth_token},
        )
        assert response.status_code == 200
