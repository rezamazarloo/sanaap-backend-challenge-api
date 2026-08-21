import logging

from celery import Task, shared_task
from document.services import DocumentService
from document.storage import ObjectStorageError

logger = logging.getLogger("document.tasks")


class ObjectStorageRetryTask(Task):
    abstract = True
    acks_late = True
    autoretry_for = (ObjectStorageError,)
    max_retries = 10
    reject_on_worker_lost = True
    retry_backoff = True
    retry_backoff_max = 300
    retry_jitter = True
    track_started = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        document_id = _document_id_from_task_args(args, kwargs)
        if isinstance(exc, ObjectStorageError) and document_id is not None:
            service = DocumentService()
            service.mark_document_upload_failed(
                document_id,
                publish_document_event=_failure_event_publisher(service, self.name),
            )
            logger.error(
                "Document %s upload failed after %s retries.",
                document_id,
                self.max_retries,
            )

        super().on_failure(exc, task_id, args, kwargs, einfo)


@shared_task(
    bind=True,
    base=ObjectStorageRetryTask,
    name="document.tasks.upload_document_task",
)
def upload_document_task(self, document_id: int):
    document = DocumentService().complete_pending_upload(document_id)
    return _document_task_result(document_id, document)


@shared_task(
    bind=True,
    base=ObjectStorageRetryTask,
    name="document.tasks.replace_document_task",
)
def replace_document_task(self, document_id: int):
    document = DocumentService().complete_pending_replacement(document_id)
    return _document_task_result(document_id, document)


@shared_task(
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
    track_started=True,
    name="document.tasks.reconcile_failed_document_uploads_task",
)
def reconcile_failed_document_uploads_task(self):
    result = DocumentService().enqueue_failed_upload_retries()
    logger.info(
        "Reconciliation enqueued %s failed document uploads.",
        result["documents"],
    )
    return result


def _document_task_result(document_id: int, document) -> dict:
    return {
        "document_id": document_id,
        "status": getattr(document, "status", None),
    }


def _document_id_from_task_args(args, kwargs):
    if "document_id" in kwargs:
        return kwargs["document_id"]
    if args:
        return args[0]
    return None


def _failure_event_publisher(service, task_name):
    if task_name == "document.tasks.upload_document_task":
        return service.event_publisher.document_uploaded
    return service.event_publisher.document_updated
