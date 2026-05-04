from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.scheduler import ScheduledTask, ScheduleType
from app.schemas.scheduler import ScheduledTaskCreate, ScheduledTaskUpdate
from app.services.common import coerce_uuid
from app.services.exceptions import BadRequestError, NotFoundError
from app.services.query_utils import apply_ordering, apply_pagination
from app.services.response import ListResponseMixin


def _validate_schedule_type(value):
    if value is None:
        return None
    if isinstance(value, ScheduleType):
        return value
    try:
        return ScheduleType(value)
    except ValueError as exc:
        raise BadRequestError("Invalid schedule_type") from exc


class ScheduledTasks(ListResponseMixin):
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: ScheduledTaskCreate):
        if payload.interval_seconds < 1:
            raise BadRequestError("interval_seconds must be >= 1")
        task = ScheduledTask(**payload.model_dump())
        self.db.add(task)
        self.db.flush()
        self.db.refresh(task)
        return task

    def get(self, task_id: str):
        task = self.db.get(ScheduledTask, coerce_uuid(task_id))
        if not task:
            raise NotFoundError("Scheduled task not found")
        return task

    def list(
        self,
        enabled: bool | None,
        order_by: str,
        order_dir: str,
        limit: int,
        offset: int,
    ):
        query = select(ScheduledTask)
        if enabled is not None:
            query = query.where(ScheduledTask.enabled == enabled)
        query = apply_ordering(
            query,
            order_by,
            order_dir,
            {"created_at": ScheduledTask.created_at, "name": ScheduledTask.name},
        )
        return self.db.scalars(apply_pagination(query, limit, offset)).all()

    def update(self, task_id: str, payload: ScheduledTaskUpdate):
        task = self.db.get(ScheduledTask, coerce_uuid(task_id))
        if not task:
            raise NotFoundError("Scheduled task not found")
        data = payload.model_dump(exclude_unset=True)
        if "schedule_type" in data:
            data["schedule_type"] = _validate_schedule_type(data["schedule_type"])
        if "interval_seconds" in data and data["interval_seconds"] is not None:
            if data["interval_seconds"] < 1:
                raise BadRequestError("interval_seconds must be >= 1")
        for key, value in data.items():
            setattr(task, key, value)
        self.db.flush()
        self.db.refresh(task)
        return task

    def delete(self, task_id: str):
        task = self.db.get(ScheduledTask, coerce_uuid(task_id))
        if not task:
            raise NotFoundError("Scheduled task not found")
        self.db.delete(task)
        self.db.flush()


def refresh_schedule() -> dict:
    return {"detail": "Celery beat refreshes schedules automatically."}


def enqueue_task(task_name: str, args: list | None, kwargs: dict | None) -> dict:
    from app.celery_app import celery_app

    async_result = celery_app.send_task(task_name, args=args or [], kwargs=kwargs or {})
    return {"queued": True, "task_id": str(async_result.id)}
