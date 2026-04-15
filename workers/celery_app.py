from celery import Celery
from celery.schedules import crontab

from core.config import settings

celery_app = Celery(
    "admin_portal",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "workers.tasks.refresh_dashboard_aggregates": {"queue": "analytics-refresh"},
        "workers.tasks.process_embedding_job": {"queue": "ai-processing"},
    },
    beat_schedule={
        # Refresh aggregates every 5 minutes via celery beat
        "refresh-dashboard-aggregates": {
            "task": "workers.tasks.refresh_dashboard_aggregates",
            "schedule": crontab(minute="*/5"),
        },
    },
)
