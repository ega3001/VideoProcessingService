from celery import Celery

from core.config import Config


celery_app = Celery(
    "vps",
    broker=Config.BROKER_URL,
    backend=Config.BACKEND_URL,
    include="api.actions.consumers",
)

celery_app.conf.task_track_started = True
