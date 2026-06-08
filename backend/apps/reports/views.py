from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from apps.incidents.models import Incident
from apps.incidents.filters import IncidentFilter
from .pdf_generator import build_incident_report


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_pdf(request):
    """RF9: Exportar reporte de incidentes en PDF con los mismos filtros del listado."""
    queryset = Incident.objects.select_related('created_by', 'assigned_to').all()
    filterset = IncidentFilter(request.query_params, queryset=queryset)
    incidents = list(filterset.qs)

    filters_desc = ', '.join(
        f"{k}={v}" for k, v in request.query_params.items()
        if v and k not in ('page', 'page_size')
    )

    buffer = build_incident_report(incidents, filters_desc)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="sgis_reporte_incidentes.pdf"'
    return response
