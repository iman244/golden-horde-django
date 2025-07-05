from rest_framework import routers
from .views import HordesViewSet

router = routers.DefaultRouter()

router.register(r'', HordesViewSet, basename='hordes')

urlpatterns = router.urls