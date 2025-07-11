import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goldenhorde.settings")

import django
django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application
from hordes.routing import websocket_urlpatterns
from .middlewares import HeaderTokenAuthMiddleware

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            HeaderTokenAuthMiddleware(URLRouter(websocket_urlpatterns))
        ),
    }
)