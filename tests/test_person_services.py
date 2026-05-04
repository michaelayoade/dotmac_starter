"""Tests for person service."""

import uuid

import pytest

from app.schemas.person import PersonCreate, PersonUpdate
from app.services import person as person_service
from app.services.exceptions import NotFoundError


def _unique_email() -> str:
    return f"test-{uuid.uuid4().hex}@example.com"


def test_create_person(db_session):
    """Test creating a person."""
    email = _unique_email()
    service = person_service.People(db_session)
    person = service.create(
        PersonCreate(
            first_name="John",
            last_name="Doe",
            email=email,
        ),
    )
    assert person.first_name == "John"
    assert person.last_name == "Doe"
    assert person.email == email
    assert person.is_active is True


def test_get_person_by_id(db_session):
    """Test getting a person by ID."""
    service = person_service.People(db_session)
    person = service.create(
        PersonCreate(
            first_name="Jane",
            last_name="Smith",
            email=_unique_email(),
        ),
    )
    fetched = service.get(str(person.id))
    assert fetched is not None
    assert fetched.id == person.id
    assert fetched.first_name == "Jane"


def test_list_people_filter_by_email(db_session):
    """Test listing people filtered by email."""
    email = _unique_email()
    service = person_service.People(db_session)
    service.create(
        PersonCreate(first_name="Alice", last_name="Test", email=email),
    )
    service.create(
        PersonCreate(first_name="Bob", last_name="Other", email=_unique_email()),
    )

    results = service.list(
        email=email,
        status=None,
        is_active=None,
        order_by="created_at",
        order_dir="asc",
        limit=10,
        offset=0,
    )
    assert len(results) == 1
    assert results[0].first_name == "Alice"


def test_list_people_filter_by_status(db_session):
    """Test listing people filtered by status."""
    service = person_service.People(db_session)
    email1 = _unique_email()
    person1 = service.create(
        PersonCreate(first_name="Active", last_name="User", email=email1),
    )
    email2 = _unique_email()
    person2 = service.create(
        PersonCreate(first_name="Inactive", last_name="User", email=email2),
    )
    # Update second person to inactive
    service.update(
        str(person2.id),
        PersonUpdate(status="inactive"),
    )

    # Query for person1 specifically with active status filter
    active_results = service.list(
        email=email1,
        status="active",
        is_active=None,
        order_by="created_at",
        order_dir="asc",
        limit=100,
        offset=0,
    )
    assert len(active_results) == 1
    assert active_results[0].id == person1.id

    # Verify person2 is not returned when filtering for active
    inactive_as_active = service.list(
        email=email2,
        status="active",
        is_active=None,
        order_by="created_at",
        order_dir="asc",
        limit=100,
        offset=0,
    )
    assert len(inactive_as_active) == 0


def test_list_people_active_only(db_session):
    """Test listing only active people."""
    service = person_service.People(db_session)
    person = service.create(
        PersonCreate(first_name="ToDelete", last_name="User", email=_unique_email()),
    )
    service.delete(str(person.id))

    results = service.list(
        email=None,
        status=None,
        is_active=True,
        order_by="created_at",
        order_dir="asc",
        limit=100,
        offset=0,
    )
    ids = {p.id for p in results}
    assert person.id not in ids


def test_update_person(db_session):
    """Test updating a person."""
    service = person_service.People(db_session)
    person = service.create(
        PersonCreate(first_name="Original", last_name="Name", email=_unique_email()),
    )
    updated = service.update(
        str(person.id),
        PersonUpdate(first_name="Updated", last_name="Person"),
    )
    assert updated.first_name == "Updated"
    assert updated.last_name == "Person"


def test_delete_person(db_session):
    """Test deleting a person."""
    service = person_service.People(db_session)
    person = service.create(
        PersonCreate(first_name="ToDelete", last_name="User", email=_unique_email()),
    )
    person_id = person.id
    service.delete(str(person_id))

    # Verify person is deleted
    with pytest.raises(NotFoundError):
        service.get(str(person_id))


def test_list_people_pagination(db_session):
    """Test pagination of people list."""
    service = person_service.People(db_session)
    # Create multiple people
    for i in range(5):
        service.create(
            PersonCreate(
                first_name=f"Person{i}",
                last_name="Test",
                email=_unique_email(),
            ),
        )

    page1 = service.list(
        email=None,
        status=None,
        is_active=None,
        order_by="created_at",
        order_dir="asc",
        limit=2,
        offset=0,
    )
    page2 = service.list(
        email=None,
        status=None,
        is_active=None,
        order_by="created_at",
        order_dir="asc",
        limit=2,
        offset=2,
    )

    assert len(page1) == 2
    assert len(page2) == 2
    # Pages should have different people
    page1_ids = {p.id for p in page1}
    page2_ids = {p.id for p in page2}
    assert page1_ids.isdisjoint(page2_ids)
