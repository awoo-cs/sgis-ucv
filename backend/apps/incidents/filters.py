import django_filters
from .models import Incident


class IncidentFilter(django_filters.FilterSet):
    detected_from = django_filters.DateFilter(field_name='detected_at', lookup_expr='gte')
    detected_to = django_filters.DateFilter(field_name='detected_at', lookup_expr='lte')
    created_from = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')
    created_to = django_filters.DateFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = Incident
        fields = {
            'incident_type': ['exact'],
            'criticality': ['exact'],
            'status': ['exact'],
            'affected_area': ['icontains'],
            'assigned_to': ['exact'],
            'created_by': ['exact'],
        }
