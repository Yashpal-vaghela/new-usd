from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/voice-agent/', consumers.VoiceAgentConsumer.as_asgi()),
]
