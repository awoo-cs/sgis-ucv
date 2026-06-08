from rest_framework import generics
from apps.accounts.permissions import IsAdminTIOrAnalista
from .models import ActionPlan
from .serializers import ActionPlanSerializer


class ActionPlanDetailView(generics.RetrieveUpdateAPIView):
    queryset = ActionPlan.objects.select_related('incident')
    serializer_class = ActionPlanSerializer

    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH'):
            return [IsAdminTIOrAnalista()]
        from rest_framework.permissions import IsAuthenticated
        return [IsAuthenticated()]
