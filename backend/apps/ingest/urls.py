from django.urls import path
from .views import (EventIngestView, OperationsFeedView, BlocklistView,
                    ReleaseBlockView, ResetDemoView)

urlpatterns = [
    path('events/', EventIngestView.as_view(), name='ingest-events'),
    path('feed/', OperationsFeedView.as_view(), name='ingest-feed'),
    path('blocklist/', BlocklistView.as_view(), name='ingest-blocklist'),
    path('blocklist/<str:source_ip>/release/', ReleaseBlockView.as_view(), name='ingest-release'),
    path('reset/', ResetDemoView.as_view(), name='ingest-reset'),
]
