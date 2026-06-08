from django.db.models import Count, Avg, F, ExpressionWrapper, DurationField
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import IsAdminTIOrAnalista
from apps.action_plans.plan_templates import generate_action_plan
from .filters import IncidentFilter
from .models import Incident, IncidentComment
from .serializers import (
    IncidentListSerializer, IncidentDetailSerializer,
    IncidentCreateSerializer, IncidentUpdateSerializer,
    IncidentCommentSerializer,
)


class IncidentListCreateView(generics.ListCreateAPIView):
    queryset = Incident.objects.select_related('created_by', 'assigned_to').all()
    filterset_class = IncidentFilter
    search_fields = ['title', 'description', 'affected_area', 'affected_system']
    ordering_fields = ['created_at', 'detected_at', 'criticality', 'status']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return IncidentCreateSerializer
        return IncidentListSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminTIOrAnalista()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        incident = serializer.save()
        # RF6: Generar plan de acción automático
        generate_action_plan(incident)


class IncidentDetailView(generics.RetrieveUpdateAPIView):
    queryset = Incident.objects.prefetch_related(
        'status_history__changed_by',
        'comments__author',
    ).select_related('created_by', 'assigned_to')

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return IncidentUpdateSerializer
        return IncidentDetailSerializer

    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH'):
            return [IsAdminTIOrAnalista()]
        return [IsAuthenticated()]


class IncidentCommentCreateView(generics.CreateAPIView):
    serializer_class = IncidentCommentSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        incident_pk = self.kwargs['pk']
        incident = Incident.objects.get(pk=incident_pk)
        serializer.save(incident=incident, author=self.request.user)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_metrics(request):
    """RF7: Métricas del dashboard."""
    now = timezone.now()
    thirty_days_ago = now - timezone.timedelta(days=30)

    total = Incident.objects.count()
    active_critical = Incident.objects.filter(
        criticality=Incident.CRITICO,
        status__in=[Incident.ABIERTO, Incident.EN_INVESTIGACION]
    ).count()

    by_status = list(
        Incident.objects.values('status').annotate(count=Count('id'))
    )
    by_type = list(
        Incident.objects.values('incident_type').annotate(count=Count('id'))
    )
    by_criticality = list(
        Incident.objects.values('criticality').annotate(count=Count('id'))
    )

    recent_by_month = list(
        Incident.objects.filter(created_at__gte=thirty_days_ago)
        .extra(select={'day': "date(created_at)"})
        .values('day').annotate(count=Count('id'))
        .order_by('day')
    )

    return Response({
        'total': total,
        'active_critical': active_critical,
        'by_status': by_status,
        'by_type': by_type,
        'by_criticality': by_criticality,
        'recent_by_month': recent_by_month,
    })
