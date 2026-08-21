import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings

logger = logging.getLogger("notification.publishers")


class DocumentEventPublisher:
    def __init__(self, channel_layer=None):
        self.channel_layer = channel_layer or get_channel_layer()

    def document_uploaded(self, document):
        self._publish(
            {
                "event": "document.uploaded",
                "document_id": document.pk,
                "status": document.status,
            }
        )

    def document_updated(self, document):
        self._publish(
            {
                "event": "document.updated",
                "document_id": document.pk,
                "status": document.status,
            }
        )

    def _publish(self, payload):
        if self.channel_layer is None:
            logger.warning(
                "Document notification skipped; no channel layer configured."
            )
            return

        try:
            async_to_sync(self.channel_layer.group_send)(
                settings.NOTIFICATIONS_CHANNEL_GROUP_NAME,
                {
                    "type": "notification.event",
                    "payload": payload,
                },
            )
        except Exception:
            logger.exception("Failed to publish document notification.")
