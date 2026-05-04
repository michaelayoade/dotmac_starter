# DotMac Starter — Claude Agent Guide

FastAPI + SQLAlchemy 2.0 + Jinja2/HTMX/Alpine.js + PostgreSQL. Base template for new DotMac apps.
Port 8001. Plugin: `frontend-design`.

## Non-Negotiable Rules
- SQLAlchemy 2.0: `select()` + `scalars()`, never `db.query()`
- `db.flush()` in services, NOT `db.commit()` — routes commit
- Services raise `DomainError` subclasses from `app.services.exceptions`; routes should let app-level handlers translate them unless a route has a documented response-shape exception
- Routes are thin wrappers — no business logic inside
- Write routes use `_commit()` for delete/void operations and `_commit_and_refresh()` for create/update operations that return ORM models
- SQLite in-memory for tests
- Commands: always `poetry run ruff`, `poetry run mypy`, `poetry run pytest`

## Template Rules (same as ERP)
- Single quotes on `x-data` with `tojson`
- `{{ var if var else '' }}` not `{{ var | default('') }}`
- Dict lookup for dynamic Tailwind classes
- `| safe` only for CSRF, `tojson`, admin CSS
- `status_badge()`, `empty_state()`, `live_search()` macros — never inline
- Every `{% for %}` needs `{% else %}` + `empty_state()`
- CSRF mandatory on every POST form
- `<div id="results-container">` on list pages
- `scope="col"` on all `<th>`
- Dark mode: always pair `bg-white dark:bg-slate-800`

## Service Pattern
```python
class SomeService:
    def __init__(self, db: Session):
        self.db = db
    def create(self, data) -> Model:
        record = Model(**data.model_dump())
        self.db.add(record)
        self.db.flush()
        return record
```

## Security
- Never bare `except:`
- Never `| safe` on user content
- File uploads via `FileUploadService` only
- `resolve_safe_path()` for all path operations
