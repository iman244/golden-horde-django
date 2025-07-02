import json
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer


class VoiceChatConsumer(WebsocketConsumer):
    connected_users = set()  # Class-level set to track channel names

    def connect(self):
        print("Connected")
        # Use a unique group name, e.g., based on URL or horde id
        self.room_group_name = "voice_chat_tent_1"
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )
        VoiceChatConsumer.connected_users.add(self.channel_name)
        print(f"Connected users: {len(VoiceChatConsumer.connected_users)}")
        self.accept()

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )
        VoiceChatConsumer.connected_users.discard(self.channel_name)
        print(f"Connected users: {len(VoiceChatConsumer.connected_users)}")

    def receive(self, text_data):
        print("Sender channel:", self.channel_name)

        text_data_json = json.loads(text_data)
        print("Received data:", text_data_json.get("type"))
        # Handle ping from frontend
        if text_data_json.get("type") == "ping":
            # Optionally, respond with a pong
            self.send(text_data=json.dumps({"type": "pong", "ts": text_data_json.get("ts")}))
            return
        # Send to group (all users in the room)
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                "type": "voice_chat_config",
                "data": text_data_json,
                "sender_channel": self.channel_name,
            }
        )

    def voice_chat_config(self, event):
        # Only send to users except the sender
        if event["sender_channel"] != self.channel_name:
            self.send(text_data=json.dumps(event["data"]))
