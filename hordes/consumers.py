import json
from channels.generic.websocket import AsyncWebsocketConsumer
from collections import defaultdict
from .models import Tent, TentParticipant
from django.db import models
from asgiref.sync import sync_to_async
from django.core.cache import cache


class TentEventsConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.group_name = "tent_events"

    async def connect(self):
        user = self.scope.get("user")
        if not user or user.is_anonymous:
            await self.close()
            return
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()
        # Send current users in all tents
        tent_users = defaultdict(list)
        participants = await self.get_all_participants()
        for participant in participants:
            tent_users[str(participant["tent_id"])].append(participant["username"])
        await self.send(text_data=json.dumps({
            "type": "current_tent_users",
            "tents": tent_users
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def tent_event(self, event):
        await self.send(text_data=json.dumps(event["data"]))

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        # Handle ping from frontend
        if text_data_json.get("type") == "ping":
            await self.send(text_data=json.dumps({"type": "pong", "ts": text_data_json.get("ts")}))
            return

    @staticmethod
    async def get_all_participants():
        @sync_to_async
        def fetch():
            return list(TentParticipant.objects.select_related('user').values('tent_id', 'user__username'))
        participants = await fetch()
        # Rename user__username to username for easier use
        for p in participants:
            p["username"] = p.pop("user__username")
        return participants


class VoiceChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or user.is_anonymous:
            await self.close()
            return
        username = user.username
        # Register the user's channel name in cache (for 1 hour)
        cache.set(f"ws_channel_{username}", self.channel_name)
        print(f"WebSocket connection attempt from {self.scope.get('client', 'unknown')}")
        print(f"Headers: {self.scope.get('headers', [])}")
        print(f"Path: {self.scope.get('path', 'unknown')}")
        print("self.scope['url_route']['kwargs']", self.scope['url_route']['kwargs'])
        self.tent_id = self.scope['url_route']['kwargs']['tent_id']
        self.voice_chat_tent_id = f"voice_chat_{self.tent_id}"
        print(f"Connecting to tent: {self.tent_id}")

        await self.channel_layer.group_add(
            self.voice_chat_tent_id,
            self.channel_name
        )

        # Fetch tent once and handle if it does not exist
        tent = await self.get_tent(self.tent_id)
        if tent is None:
            await self.close()
            return
        # Create TentParticipant entry using authenticated user
        await self.create_tent_participant(tent, user)

        await self.accept()
        # Get other users in the tent (excluding self)
        other_users = await self.get_other_users(tent, user)
        await self.send(text_data=json.dumps({
            "type": "connect_info",
            "username": username,
            "other_users": other_users,
        }))
        print("WebSocket connection accepted successfully")
        # Broadcast join event to tent_events group

        await self.channel_layer.group_send(
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
        # Broadcast join event to the tent's own group
        await self.channel_layer.group_send(
            self.voice_chat_tent_id,
            {
                "type": "tent_event",
                "data": {
                    "type": "user_joined",
                    "tent_id": self.tent_id,
                    "username": username,
                }
            }
        )

    async def disconnect(self, close_code):
        print(f"WebSocket disconnected with code: {close_code}")
        # Remove the user's channel name from cache
        user = self.scope.get("user")
        if user and not user.is_anonymous:
            cache.delete(f"ws_channel_{user.username}")
        await self.channel_layer.group_discard(
            self.voice_chat_tent_id,
            self.channel_name
        )
        # Remove TentParticipant entry
        tent = await self.get_tent(self.tent_id)
        if tent is not None:
            await self.delete_tent_participant(tent, self.scope["user"])
        # Broadcast leave event to tent_events group
        await self.channel_layer.group_send(
            "tent_events",
            {
                "type": "tent_event",
                "data": {
                    "type": "user_left",
                    "tent_id": self.tent_id,
                    "username": self.scope["user"].username,
                }
            }
        )
        # Broadcast leave event to the tent's own group
        await self.channel_layer.group_send(
            self.voice_chat_tent_id,
            {
                "type": "tent_event",
                "data": {
                    "type": "user_left",
                    "tent_id": self.tent_id,
                    "username": self.scope["user"].username,
                }
            }
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        # Handle ping from frontend
        if text_data_json.get("type") == "ping":
            await self.send(text_data=json.dumps({"type": "pong", "ts": text_data_json.get("ts")}))
            return
        
        print("receive", text_data_json)

        target_username = text_data_json.get("target_user")
        print("checking the target_user", target_username)
        if target_username:
            print("we must send to target user")
            # Look up the target user's channel name in cache
            target_channel = cache.get(f"ws_channel_{target_username}")
            if target_channel:
                await self.channel_layer.send(
                    target_channel,
                    {
                        "type": "voice_chat_config",
                        "data": text_data_json,
                        "sender_channel": self.channel_name,
                    }
                )
            else:
                print(f"User {target_username} is not connected.")
        else:
            # Send to group (all users in the room)
            await self.channel_layer.group_send(
                self.voice_chat_tent_id,
                {
                    "type": "voice_chat_config",
                    "data": text_data_json,
                    "sender_channel": self.channel_name,
                }
            )

    async def voice_chat_config(self, event):
        print("voice_chat_config", event["data"])
        await self.send(text_data=json.dumps(event["data"]))

    async def tent_event(self, event):
        await self.send(text_data=json.dumps(event["data"]))

    @staticmethod
    async def get_tent(tent_id):
        @sync_to_async
        def fetch():
            try:
                return Tent.objects.get(pk=tent_id)
            except Tent.DoesNotExist:
                return None
        return await fetch()

    @staticmethod
    async def create_tent_participant(tent, user):
        @sync_to_async
        def create():
            TentParticipant.objects.get_or_create(tent=tent, user=user)
        await create()

    @staticmethod
    async def delete_tent_participant(tent, user):
        @sync_to_async
        def delete():
            TentParticipant.objects.filter(tent=tent, user=user).delete()
        await delete()

    @staticmethod
    async def get_other_users(tent, user):
        @sync_to_async
        def fetch():
            return list(TentParticipant.objects.filter(tent=tent).exclude(user=user).values_list('user__username', flat=True))
        return await fetch()
