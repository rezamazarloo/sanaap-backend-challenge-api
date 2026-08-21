import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("dms")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.conf.beat_schedule = {
    "reconcile-failed-document-uploads": {
        "task": "document.tasks.reconcile_failed_document_uploads_task",
        "schedule": 300.0,
    },
}
app.autodiscover_tasks()
