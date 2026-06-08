from django.urls import path
from .views import export_pdf

urlpatterns = [
    path('pdf/', export_pdf, name='export_pdf'),
]
