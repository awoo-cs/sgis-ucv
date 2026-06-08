from django.urls import path
from .views import IncidentListCreateView, IncidentDetailView, IncidentCommentCreateView, dashboard_metrics

urlpatterns = [
    path('', IncidentListCreateView.as_view(), name='incident_list_create'),
    path('<int:pk>/', IncidentDetailView.as_view(), name='incident_detail'),
    path('<int:pk>/comments/', IncidentCommentCreateView.as_view(), name='incident_comment_create'),
    path('dashboard/', dashboard_metrics, name='dashboard_metrics'),
]
