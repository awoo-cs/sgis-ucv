from rest_framework import serializers
from .models import SecurityEvent


class EventIngestSerializer(serializers.ModelSerializer):
    """Valida el evento que llega del sensor (frontera de confianza)."""
    class Meta:
        model = SecurityEvent
        fields = ['event_type', 'source_ip', 'dest_port', 'username', 'detail', 'sensor', 'raw']

    def create(self, validated_data):
        return SecurityEvent.objects.create(**validated_data)


class SecurityEventSerializer(serializers.ModelSerializer):
    """Salida para el feed del Centro de Operaciones."""
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)

    class Meta:
        model = SecurityEvent
        fields = [
            'id', 'received_at', 'event_type', 'event_type_display', 'source_ip',
            'dest_port', 'username', 'detail', 'sensor', 'is_alert', 'rule',
            'triggered_incident',
        ]
