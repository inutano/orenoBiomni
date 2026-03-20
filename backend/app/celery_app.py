from celery import Celery

from .config import settings

celery = Celery("orenoiomni")

celery.conf.update(
    broker_url=settings.redis_url,
    result_backend=settings.redis_url,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_soft_time_limit=settings.celery_task_timeout,
    task_time_limit=settings.celery_task_timeout + 30,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "backend.app.tasks.execute.*": {"queue": "code"},
        "backend.app.tasks.pipeline_callback.*": {"queue": "code"},
    },
)

celery.conf.update(include=["backend.app.tasks.execute", "backend.app.tasks.pipeline_callback"])
