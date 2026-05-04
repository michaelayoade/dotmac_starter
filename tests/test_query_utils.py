import enum

import pytest
from sqlalchemy import Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

from app.services.exceptions import BadRequestError
from app.services.query_utils import apply_ordering, validate_enum


class _Base(DeclarativeBase):
    pass


class _Item(_Base):
    __tablename__ = "query_utils_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)


class _Status(enum.Enum):
    active = "active"
    archived = "archived"


@pytest.fixture()
def db() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    _Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        session.add_all([_Item(id=1, name="b"), _Item(id=2, name="a")])
        session.commit()
        yield session
    finally:
        session.close()


def test_apply_ordering_raises_domain_error_for_invalid_column(db: Session) -> None:
    query = select(_Item)
    with pytest.raises(BadRequestError) as exc:
        apply_ordering(query, "missing", "asc", {"name": _Item.name})
    assert "Invalid order_by" in str(exc.value)


def test_apply_ordering_orders_valid_column(db: Session) -> None:
    query = apply_ordering(select(_Item), "name", "asc", {"name": _Item.name})
    items = list(db.scalars(query).all())
    assert [item.name for item in items] == ["a", "b"]


def test_validate_enum_raises_domain_error() -> None:
    with pytest.raises(BadRequestError) as exc:
        validate_enum("bad", _Status, "status")
    assert str(exc.value) == "Invalid status"


def test_validate_enum_returns_enum_value() -> None:
    assert validate_enum("active", _Status, "status") is _Status.active
