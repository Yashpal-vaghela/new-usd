import os
import django
from django.conf import settings
from channels.routing import ProtocolTypeRouter, URLRouter
import voice_agent.routing

if not settings.configured:
    settings.configure(
        SECRET_KEY="voice-agent-cloud-run-production-secret-key",
        DEBUG=False,
        ALLOWED_HOSTS=["*"],
        INSTALLED_APPS=[
            "daphne",
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "channels",
            "voice_agent",
        ],
        ASGI_APPLICATION="standalone_asgi.application",
        TIME_ZONE="Asia/Kolkata",
        USE_TZ=True,
    )
    django.setup()

async def http_app(scope, receive, send):
    if scope['type'] == 'http':
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [(b'content-type', b'text/plain')],
        })
        await send({
            'type': 'http.response.body',
            'body': b'Voice Agent Cloud Run Service is Active and Healthy',
        })

application = ProtocolTypeRouter({
    "http": http_app,
    "websocket": URLRouter(
        voice_agent.routing.websocket_urlpatterns
    ),
})
