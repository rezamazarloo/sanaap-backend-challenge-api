import json

from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return

        await self.channel_layer.group_add(
            settings.NOTIFICATIONS_CHANNEL_GROUP_NAME,
            self.channel_name,
        )
        await self.accept()

    async def disconnect(self, close_code):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            return

        await self.channel_layer.group_discard(
            settings.NOTIFICATIONS_CHANNEL_GROUP_NAME,
            self.channel_name,
        )

    async def notification_event(self, event):
        await self.send(text_data=json.dumps(event["payload"]))
