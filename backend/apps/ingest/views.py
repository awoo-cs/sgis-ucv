import hmac

from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.incidents.models import Incident
from .detection import evaluate
from .models import SecurityEvent
from .serializers import EventIngestSerializer, SecurityEventSerializer


class HasIngestAPIKey(BasePermission):
    """El sensor se autentica con una clave estática en la cabecera X-API-Key."""
    message = 'API-key inválida o ausente.'

    def has_permission(self, request, view):
        key = request.headers.get('X-API-Key', '')
        # compare_digest = comparación en tiempo constante (no filtra la clave por timing).
        return bool(key) and hmac.compare_digest(key, settings.INGEST_API_KEY)


class EventIngestView(APIView):
    """POST /api/ingest/events/ — recibe un evento del sensor y corre el motor de reglas."""
    authentication_classes = []          # solo API-key; sin JWT/sesión → sin CSRF
    permission_classes = [HasIngestAPIKey]

    def post(self, request):
        serializer = EventIngestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = serializer.save()
        result = evaluate(event)         # puede crear un incidente automático
        return Response(
            {'event_id': event.id, 'detection': result},
            status=status.HTTP_201_CREATED,
        )


class OperationsFeedView(APIView):
    """GET /api/ingest/feed/ — estado en vivo para el Centro de Operaciones."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        active_since = now - timezone.timedelta(minutes=5)
        events_qs = SecurityEvent.objects.all()

        recent_incidents = (
            Incident.objects.filter(created_by__username='sensor')
            .select_related('created_by')[:8]
        )

        return Response({
            'counts': {
                'events': events_qs.count(),
                'alerts': events_qs.filter(is_alert=True).count(),
                'incidents': Incident.objects.filter(created_by__username='sensor').count(),
                'sensors': (
                    events_qs.filter(received_at__gte=active_since)
                    .exclude(sensor='').values('sensor').distinct().count()
                ),
            },
            'events': SecurityEventSerializer(events_qs[:40], many=True).data,
            'incidents': [
                {
                    'id': inc.id, 'title': inc.title, 'criticality': inc.criticality,
                    'status': inc.status, 'created_at': inc.created_at,
                    'affected_system': inc.affected_system,
                }
                for inc in recent_incidents
            ],
        })
