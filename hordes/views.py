from rest_framework import viewsets
from .models import Horde
from .serializers import HordeWithTentsSerializer

class HordesViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = HordeWithTentsSerializer

    def get_queryset(self):
        return Horde.objects.prefetch_related('tents')
