import hmac

from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.incidents.models import Incident, IncidentStatusHistory
from .detection import evaluate
from .maintenance import reset_demo_data
from .models import SecurityEvent, BlockedIP
from .serializers import EventIngestSerializer, SecurityEventSerializer, BlockedIPSerializer


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


class BlocklistView(APIView):
    """GET /api/ingest/blocklist/ — IPs en contención activa. El sensor la consulta y la aplica.

    Misma autenticación que la ingesta (X-API-Key): es tráfico máquina-a-máquina.
    """
    authentication_classes = []
    permission_classes = [HasIngestAPIKey]

    def get(self, request):
        ips = list(
            BlockedIP.objects.filter(active=True).values_list('source_ip', flat=True)
        )
        return Response({'blocked_ips': ips, 'count': len(ips)})


class OperationsFeedView(APIView):
    """GET /api/ingest/feed/ — estado en vivo para el Centro de Operaciones."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        active_since = now - timezone.timedelta(minutes=5)
        events_qs = SecurityEvent.objects.all()
        blocked_qs = BlockedIP.objects.filter(active=True)

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
                'blocked': blocked_qs.count(),
            },
            'blocked_ips': BlockedIPSerializer(blocked_qs[:20], many=True).data,
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


class CanManageContainment(BasePermission):
    """Revisar/liberar contenciones: solo analista o admin_ti (human-in-the-loop)."""
    message = 'Solo un analista o administrador TI puede liberar una contención.'

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role in ('analista', 'admin_ti'))


class IsAdminTI(BasePermission):
    """Acciones destructivas (reiniciar la demo): solo admin_ti."""
    message = 'Solo un administrador TI puede reiniciar la demo.'

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role == 'admin_ti')


class ReleaseBlockView(APIView):
    """POST /api/ingest/blocklist/<ip>/release/ — levanta la contención de una IP."""
    permission_classes = [IsAuthenticated, CanManageContainment]

    def post(self, request, source_ip):
        try:
            block = BlockedIP.objects.get(source_ip=source_ip, active=True)
        except BlockedIP.DoesNotExist:
            return Response({'detail': 'La IP no está en contención activa.'},
                            status=status.HTTP_404_NOT_FOUND)
        block.active = False
        block.released_at = timezone.now()
        block.save(update_fields=['active', 'released_at'])
        if block.incident_id:
            IncidentStatusHistory.objects.create(
                incident=block.incident, previous_status=block.incident.status,
                new_status=block.incident.status, changed_by=request.user,
                comment=f"Contención levantada manualmente sobre {source_ip}.",
            )
        return Response({'released': source_ip})


class ResetDemoView(APIView):
    """POST /api/ingest/reset/ — limpia el tablero para repetir la demo (admin_ti)."""
    permission_classes = [IsAuthenticated, IsAdminTI]

    def post(self, request):
        return Response(reset_demo_data())
