import json
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from .models import Tent, TentParticipant
from django.db import IntegrityError
from collections import defaultdict


class TentEventsConsumer(WebsocketConsumer):
    def connect(self):
        self.group_name = "tent_events"
        async_to_sync(self.channel_layer.group_add)(
            self.group_name,
            self.channel_name
        )
        self.accept()
        # Send current users in all tents
        tent_users = defaultdict(list)
        for participant in TentParticipant.objects.all():
            tent_users[str(participant.tent_id)].append(participant.username)
        self.send(text_data=json.dumps({
            "type": "current_tent_users",
            "tents": tent_users
        }))

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            self.group_name,
            self.channel_name
        )

    def tent_event(self, event):
        print("tent_event event[data]", event["data"])
        self.send(text_data=json.dumps(event["data"]))

    def receive(self, text_data):
        text_data_json = json.loads(text_data)
        # Handle ping from frontend
        if text_data_json.get("type") == "ping":
            self.send(text_data=json.dumps({"type": "pong", "ts": text_data_json.get("ts")}))
            return


class VoiceChatConsumer(WebsocketConsumer):
    def connect(self):
        print(f"WebSocket connection attempt from {self.scope.get('client', 'unknown')}")
        print(f"Headers: {self.scope.get('headers', [])}")
        print(f"Path: {self.scope.get('path', 'unknown')}")
        print("self.scope['url_route']['kwargs']", self.scope['url_route']['kwargs'])
        self.tent_id = self.scope['url_route']['kwargs']['tent_id']
        self.voice_chat_tent_id = f"voice_chat_{self.tent_id}"
        print(f"Connecting to tent: {self.tent_id}")

        async_to_sync(self.channel_layer.group_add)(
            self.voice_chat_tent_id,
            self.channel_name
        )

        username = self.channel_name
        # Fetch tent once and handle if it does not exist
        try:
            tent = Tent.objects.get(pk=self.tent_id)
        except Tent.DoesNotExist:
            self.close()
            return
        # Create TentParticipant entry
        TentParticipant.objects.get_or_create(tent=tent, username=username)

        self.accept()
        # Get other users in the tent (excluding self)
        other_users = list(
            TentParticipant.objects.filter(tent=tent).exclude(username=username).values_list('username', flat=True)
        )
        self.send(text_data=json.dumps({
            "type": "connect_info",
            "username": username,
            "other_users": other_users,
        }))
        print("WebSocket connection accepted successfully")
        # Broadcast join event to tent_events group

        print("it must ran")
        async_to_sync(self.channel_layer.group_send)(
            "tent_events",
            {
                "type": "tent_event",
                "data": {
                    "type": "user_joined",
                    "tent_id": self.tent_id,
                    "username": username,
                }
            }
        )

    def disconnect(self, close_code):
        print(f"WebSocket disconnected with code: {close_code}")
        async_to_sync(self.channel_layer.group_discard)(
            self.voice_chat_tent_id,
            self.channel_name
        )
        # Remove TentParticipant entry
        try:
            tent = Tent.objects.get(pk=self.tent_id)
            TentParticipant.objects.filter(tent=tent, username=self.channel_name).delete()
        except Tent.DoesNotExist:
            pass
        # Broadcast leave event to tent_events group
        async_to_sync(self.channel_layer.group_send)(
            "tent_events",
            {
                "type": "tent_event",
                "data": {
                    "type": "user_left",
                    "tent_id": self.tent_id,
                    "username": self.channel_name,
                }
            }
        )

    def receive(self, text_data):
        text_data_json = json.loads(text_data)
        # Handle ping from frontend
        if text_data_json.get("type") == "ping":
            self.send(text_data=json.dumps({"type": "pong", "ts": text_data_json.get("ts")}))
            return

        target_user = text_data_json.get("target_user")
        if target_user:
            # Send only to the target user (by username, which is channel_name for now)
            async_to_sync(self.channel_layer.send)(
                target_user,
                {
                    "type": "voice_chat_config",
                    "data": text_data_json,
                    "sender_channel": self.channel_name,
                }
            )
        else:
            # Send to group (all users in the room)
            async_to_sync(self.channel_layer.group_send)(
                self.voice_chat_tent_id,
                {
                    "type": "voice_chat_config",
                    "data": text_data_json,
                    "sender_channel": self.channel_name,
                }
            )

    def voice_chat_config(self, event):
        self.send(text_data=json.dumps(event["data"]))
