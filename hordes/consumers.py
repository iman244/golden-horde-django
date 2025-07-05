import json
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer


class VoiceChatConsumer(WebsocketConsumer):
    connected_users = {}  # {tent_id: set(channel_names)}

    def connect(self):
        print(f"WebSocket connection attempt from {self.scope.get('client', 'unknown')}")
        print(f"Headers: {self.scope.get('headers', [])}")
        print(f"Path: {self.scope.get('path', 'unknown')}")
        
        # Get room name from URL pattern
        print("self.scope['url_route']['kwargs']", self.scope['url_route']['kwargs'])
        self.tent_id = self.scope['url_route']['kwargs']['tent_id']
        self.voice_chat_tent_id = f"voice_chat_{self.tent_id}"
        
        print(f"Connecting to tent: {self.tent_id}")
        
        async_to_sync(self.channel_layer.group_add)(
            self.voice_chat_tent_id,
            self.channel_name
        )
        # Add user to the tent's set
        if self.tent_id not in VoiceChatConsumer.connected_users:
            VoiceChatConsumer.connected_users[self.tent_id] = set()
        VoiceChatConsumer.connected_users[self.tent_id].add(self.channel_name)
        print(f"Connected users in tent {self.tent_id}: {len(VoiceChatConsumer.connected_users[self.tent_id])}")
        self.accept()
        # Send connection info with both the user's channel name and other users in the same tent
        other_channels = list(VoiceChatConsumer.connected_users[self.tent_id] - {self.channel_name})
        self.send(text_data=json.dumps({
            "type": "connect_info",
            "username": self.channel_name,
            "other_users": other_channels,
        }))
        print("WebSocket connection accepted successfully")

    def disconnect(self, close_code):
        print(f"WebSocket disconnected with code: {close_code}")
        async_to_sync(self.channel_layer.group_discard)(
            self.voice_chat_tent_id,
            self.channel_name
        )
        # Remove user from the tent's set
        tent_users = VoiceChatConsumer.connected_users.get(self.tent_id)
        if tent_users:
            tent_users.discard(self.channel_name)
            if not tent_users:
                # Clean up empty tent
                del VoiceChatConsumer.connected_users[self.tent_id]
        print(f"Connected users in tent {self.tent_id}: {len(VoiceChatConsumer.connected_users.get(self.tent_id, []))}")

    def receive(self, text_data):
        text_data_json = json.loads(text_data)
        # Handle ping from frontend
        if text_data_json.get("type") == "ping":
            self.send(text_data=json.dumps({"type": "pong", "ts": text_data_json.get("ts")}))
            return

        target_user = text_data_json.get("target_user")
        if target_user:
            # Send only to the target user (by channel name)
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
