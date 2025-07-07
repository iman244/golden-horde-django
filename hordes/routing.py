# chat/routing.py
from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/voice_chat/(?P<tent_id>\w+)/$", consumers.VoiceChatConsumer.as_asgi()),
    re_path(r"ws/tent-events/$", consumers.TentEventsConsumer.as_asgi()),
]