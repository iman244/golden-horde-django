import logging
import json
from collections import defaultdict
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.cache import cache
from django.conf import settings
from .models import Tent, TentParticipant

logger = logging.getLogger(__name__)


class CacheManager:
    """Utility class for managing WebSocket user cache operations"""
    
    # Default TTL for WebSocket connections (can be extended)
    DEFAULT_WS_TTL = getattr(settings, 'WS_CACHE_TTL', 3600)  # 1 hour default
    # Extended TTL for long-running connections
    EXTENDED_WS_TTL = getattr(settings, 'WS_CACHE_EXTENDED_TTL', 86400)  # 24 hours default
    
    @staticmethod
    def get_user_channel_key(username):
        """Generate cache key for user's WebSocket channel"""
        return f"ws_channel_{username}"
    
    @staticmethod
    def get_user_tent_key(username):
        """Generate cache key for user's current tent"""
        return f"ws_tent_{username}"
    
    @staticmethod
    def set_user_channel(username, channel_name, timeout=None):
        """Set user's WebSocket channel in cache"""
        if timeout is None:
            timeout = CacheManager.DEFAULT_WS_TTL
            
        try:
            cache_key = CacheManager.get_user_channel_key(username)
            cache.set(cache_key, channel_name, timeout=timeout)
            logger.info(f"User {username} channel registered in cache: {channel_name} (TTL: {timeout}s)")
            return True
        except Exception as e:
            logger.error(f"Failed to set cache for user {username}: {e}")
            return False
    
    @staticmethod
    def get_user_channel(username):
        """Get user's WebSocket channel from cache"""
        try:
            cache_key = CacheManager.get_user_channel_key(username)
            return cache.get(cache_key)
        except Exception as e:
            logger.error(f"Failed to get cache for user {username}: {e}")
            return None
    
    @staticmethod
    def delete_user_channel(username):
        """Delete user's WebSocket channel from cache"""
        try:
            cache_key = CacheManager.get_user_channel_key(username)
            cache.delete(cache_key)
            logger.info(f"User {username} channel removed from cache")
            return True
        except Exception as e:
            logger.error(f"Failed to delete cache for user {username}: {e}")
            return False
    
    @staticmethod
    def extend_user_channel_ttl(username, timeout=None):
        """Extend the TTL for a user's channel cache entry"""
        if timeout is None:
            timeout = CacheManager.EXTENDED_WS_TTL
            
        try:
            cache_key = CacheManager.get_user_channel_key(username)
            current_value = cache.get(cache_key)
            if current_value:
                cache.set(cache_key, current_value, timeout=timeout)
                logger.info(f"Extended TTL for user {username} channel to {timeout}s")
                return True
            else:
                logger.warning(f"Cannot extend TTL for user {username}: channel not found in cache")
                return False
        except Exception as e:
            logger.error(f"Failed to extend TTL for user {username}: {e}")
            return False
    
    @staticmethod
    def set_user_tent(username, tent_id, timeout=None):
        """Set user's current tent in cache"""
        if timeout is None:
            timeout = CacheManager.DEFAULT_WS_TTL
            
        try:
            cache_key = CacheManager.get_user_tent_key(username)
            cache.set(cache_key, tent_id, timeout=timeout)
            return True
        except Exception as e:
            logger.error(f"Failed to set tent cache for user {username}: {e}")
            return False
    
    @staticmethod
    def get_user_tent(username):
        """Get user's current tent from cache"""
        try:
            cache_key = CacheManager.get_user_tent_key(username)
            return cache.get(cache_key)
        except Exception as e:
            logger.error(f"Failed to get tent cache for user {username}: {e}")
            return None
    
    @staticmethod
    def extend_user_tent_ttl(username, timeout=None):
        """Extend the TTL for a user's tent cache entry"""
        if timeout is None:
            timeout = CacheManager.EXTENDED_WS_TTL
            
        try:
            cache_key = CacheManager.get_user_tent_key(username)
            current_value = cache.get(cache_key)
            if current_value:
                cache.set(cache_key, current_value, timeout=timeout)
                logger.info(f"Extended TTL for user {username} tent to {timeout}s")
                return True
            else:
                logger.warning(f"Cannot extend TTL for user {username}: tent not found in cache")
                return False
        except Exception as e:
            logger.error(f"Failed to extend tent TTL for user {username}: {e}")
            return False


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
        
        # Register the user's channel name in cache with extended TTL for long connections
        CacheManager.set_user_channel(username, self.channel_name, timeout=CacheManager.EXTENDED_WS_TTL)
        
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
        
        # Store user's current tent in cache with extended TTL
        CacheManager.set_user_tent(username, self.tent_id, timeout=CacheManager.EXTENDED_WS_TTL)

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
        print(f"WebSocket VoiceChatConsumer disconnected with code: {close_code}")
        
        # Remove the user's channel name and tent from cache
        user = self.scope.get("user")
        if user and not user.is_anonymous:
            CacheManager.delete_user_channel(user.username)
            # Also remove tent association
            cache.delete(CacheManager.get_user_tent_key(user.username))
        
        await self.channel_layer.group_discard(
            self.voice_chat_tent_id,
            self.channel_name
        )
        # Remove TentParticipant entry
        tent = await self.get_tent(self.tent_id)
        print("VoiceChatConsumer disconnect user tent", user.username, tent)
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
            username = self.scope['user'].username
            print(f"ping from {username} from channel_name: {self.channel_name}")
            
            # Extend cache TTL on ping to support long-running connections
            CacheManager.extend_user_channel_ttl(username)
            CacheManager.extend_user_tent_ttl(username)
            
            await self.send(text_data=json.dumps({"type": "pong", "ts": text_data_json.get("ts")}))
            return
        
        print("receive", text_data_json)

        target_username = text_data_json.get("target_user")
        if target_username:
            # Check if target user is a participant in the tent
            is_participant = await self.is_tent_participant(self.tent_id, target_username)
            if not is_participant:
                print(target_username, "was not participant")
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "target_user": target_username,
                    "message": f"User {target_username} is not a participant in this tent."
                }))
                return
            # Look up the target user's channel name in cache
            target_channel = CacheManager.get_user_channel(target_username)
            print("checking the target_channel for target_user", target_username, target_channel)
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
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "target_user": target_username,
                    "message": f"User {target_username} is not currently connected."
                }))
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

    @staticmethod
    async def is_tent_participant(tent_id, username):
        @sync_to_async
        def check():
            return TentParticipant.objects.filter(
                tent__pk=tent_id, user__username=username
            ).exists()
        return await check()
