from rest_framework import viewsets, authentication
from .models import Horde
from .serializers import HordeWithTentsSerializer

class HordesViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = HordeWithTentsSerializer
    authentication_classes = [authentication.TokenAuthentication]

    def get_queryset(self):
        return Horde.objects.prefetch_related('tents')
