from __future__ import annotations

from app.celery_app import celery_app


@celery_app.task(name="app.tasks.example.ping")
def ping(message: str = "pong") -> dict[str, str]:
    return {"message": message}
