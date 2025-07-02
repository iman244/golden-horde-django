# chat/routing.py
from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/voice_chat/(?P<room_name>\w+)/$", consumers.VoiceChatConsumer.as_asgi()),
]