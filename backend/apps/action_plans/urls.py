from django.urls import path
from .views import ActionPlanDetailView

urlpatterns = [
    path('<int:pk>/', ActionPlanDetailView.as_view(), name='action_plan_detail'),
]
