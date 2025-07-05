from rest_framework import serializers
from .models import Horde, Tent

class TentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tent
        fields = "__all__"


class HordeWithTentsSerializer(serializers.ModelSerializer):
    tents = TentSerializer(many=True)
    class Meta:
        model = Horde
        fields = "__all__"