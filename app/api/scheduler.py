from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.common import ListResponse
from app.schemas.scheduler import (
    ScheduledTaskCreate,
    ScheduledTaskRead,
    ScheduledTaskUpdate,
)
from app.services import scheduler as scheduler_service

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


def _commit(db: Session) -> None:
    db.commit()


def _commit_and_refresh(db: Session, result):
    _commit(db)
    db.refresh(result)
    return result


@router.get("/tasks", response_model=ListResponse[ScheduledTaskRead])
def list_scheduled_tasks(
    enabled: bool | None = None,
    order_by: str = Query(default="created_at"),
    order_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return scheduler_service.ScheduledTasks(db).list_response(
        enabled, order_by, order_dir, limit, offset
    )


@router.post(
    "/tasks",
    response_model=ScheduledTaskRead,
    status_code=status.HTTP_201_CREATED,
)
def create_scheduled_task(payload: ScheduledTaskCreate, db: Session = Depends(get_db)):
    task = scheduler_service.ScheduledTasks(db).create(payload)
    return _commit_and_refresh(db, task)


@router.get("/tasks/{task_id}", response_model=ScheduledTaskRead)
def get_scheduled_task(task_id: str, db: Session = Depends(get_db)):
    return scheduler_service.ScheduledTasks(db).get(task_id)


@router.patch("/tasks/{task_id}", response_model=ScheduledTaskRead)
def update_scheduled_task(
    task_id: str, payload: ScheduledTaskUpdate, db: Session = Depends(get_db)
):
    task = scheduler_service.ScheduledTasks(db).update(task_id, payload)
    return _commit_and_refresh(db, task)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scheduled_task(task_id: str, db: Session = Depends(get_db)):
    scheduler_service.ScheduledTasks(db).delete(task_id)
    _commit(db)


@router.post("/tasks/refresh", status_code=status.HTTP_200_OK)
def refresh_schedule():
    return scheduler_service.refresh_schedule()


@router.post("/tasks/{task_id}/enqueue", status_code=status.HTTP_202_ACCEPTED)
def enqueue_scheduled_task(task_id: str, db: Session = Depends(get_db)):
    task = scheduler_service.ScheduledTasks(db).get(task_id)
    return scheduler_service.enqueue_task(
        task.task_name, task.args_json or [], task.kwargs_json or {}
    )
