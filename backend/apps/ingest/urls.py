from django.urls import path
from .views import EventIngestView, OperationsFeedView

urlpatterns = [
    path('events/', EventIngestView.as_view(), name='ingest-events'),
    path('feed/', OperationsFeedView.as_view(), name='ingest-feed'),
]
