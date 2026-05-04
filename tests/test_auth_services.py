import hashlib

import pytest

from app.models.auth import SessionStatus
from app.schemas.auth import (
    ApiKeyGenerateRequest,
    MFAMethodCreate,
    SessionCreate,
    UserCredentialCreate,
)
from app.services import auth as auth_service
from app.services.auth_flow import hash_password
from app.services.exceptions import ServiceUnavailableError


class _FakeRedis:
    def __init__(self):
        self.store = {}

    def incr(self, key):
        self.store[key] = int(self.store.get(key, 0)) + 1
        return self.store[key]

    def expire(self, key, _seconds):
        return True


def test_user_credentials_soft_delete(db_session, person):
    service = auth_service.UserCredentials(db_session)
    payload = UserCredentialCreate(
        person_id=person.id,
        username="user@example.com",
        password_hash=hash_password("secret"),
    )
    credential = service.create(payload)
    active = service.list(
        person_id=str(person.id),
        provider=None,
        is_active=None,
        order_by="created_at",
        order_dir="desc",
        limit=25,
        offset=0,
    )
    assert len(active) == 1
    service.delete(str(credential.id))
    active = service.list(
        person_id=str(person.id),
        provider=None,
        is_active=None,
        order_by="created_at",
        order_dir="desc",
        limit=25,
        offset=0,
    )
    inactive = service.list(
        person_id=str(person.id),
        provider=None,
        is_active=False,
        order_by="created_at",
        order_dir="desc",
        limit=25,
        offset=0,
    )
    assert active == []
    assert len(inactive) == 1


def test_mfa_primary_switch(db_session, person):
    service = auth_service.MFAMethods(db_session)
    payload = MFAMethodCreate(
        person_id=person.id,
        method_type="totp",
        label="primary",
        secret="encrypted",
        is_primary=True,
        enabled=True,
    )
    first = service.create(payload)
    second = service.create(
        MFAMethodCreate(
            person_id=person.id,
            method_type="totp",
            label="secondary",
            secret="encrypted2",
            is_primary=True,
            enabled=True,
        ),
    )
    db_session.refresh(first)
    db_session.refresh(second)
    assert first.is_primary is False
    assert second.is_primary is True


def test_session_delete_revokes(db_session, person):
    service = auth_service.Sessions(db_session)
    payload = SessionCreate(
        person_id=person.id,
        status=SessionStatus.active,
        token_hash="hash",
        ip_address="127.0.0.1",
        user_agent="pytest",
        expires_at="2099-01-01T00:00:00+00:00",
    )
    session = service.create(payload)
    service.delete(str(session.id))
    db_session.refresh(session)
    assert session.status == SessionStatus.revoked
    assert session.revoked_at is not None


def test_api_key_generate_with_redis(monkeypatch, db_session):
    fake = _FakeRedis()
    monkeypatch.setattr(auth_service, "_get_redis_client", lambda: fake)
    payload = ApiKeyGenerateRequest(label="test")
    result = auth_service.ApiKeys(db_session).generate_with_rate_limit(payload, None)
    raw_key = result["key"]
    api_key = result["api_key"]
    assert auth_service.hash_api_key(raw_key) == api_key.key_hash
    assert hashlib.sha256(raw_key.encode("utf-8")).hexdigest() != api_key.key_hash


def test_api_key_rate_limit_requires_redis(monkeypatch, db_session):
    monkeypatch.setattr(auth_service, "_get_redis_client", lambda: None)
    with pytest.raises(ServiceUnavailableError) as exc:
        auth_service.ApiKeys(db_session).generate_with_rate_limit(
            ApiKeyGenerateRequest(label="test"), None
        )
    assert str(exc.value) == "Rate limiting unavailable (Redis required)"
