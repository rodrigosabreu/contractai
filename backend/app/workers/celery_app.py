"""Celery configuration for async task processing."""
from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "contractai",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=settings.CELERY_TASK_TRACK_STARTED,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    task_soft_time_limit=settings.CELERY_TASK_SOFT_TIME_LIMIT,
    worker_prefetch_multiplier=settings.CELERY_WORKER_PREFETCH_MULTIPLIER,
    worker_max_tasks_per_child=settings.CELERY_WORKER_MAX_TASKS_PER_CHILD,
    result_expires=3600,
    task_acks_late=True,
    worker_disable_rate_limits=True,
    # Retry policy
    task_autoretry_for=(Exception,),
    task_retry_backoff=True,
    task_retry_backoff_max=600,
    task_retry_jitter=True,
    # Routing
    task_routes={
        "app.workers.tasks.analyze_contract": {"queue": "analysis"},
        "app.workers.tasks.sync_connector": {"queue": "connectors"},
    },
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "cleanup-expired-tokens": {
        "task": "app.workers.tasks.cleanup_expired_tokens",
        "schedule": 3600.0,  # Every hour
    },
    "cleanup-old-audit-logs": {
        "task": "app.workers.tasks.cleanup_old_audit_logs",
        "schedule": 86400.0,  # Daily
    },
}