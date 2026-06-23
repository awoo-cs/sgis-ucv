from rest_framework.permissions import BasePermission


class IsAdminTI(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_admin_ti


class IsAdminTIOrAnalista(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_admin_ti or request.user.is_analista
        )


class IsJefeArea(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_jefe_area


class CanUpdateOrValidateIncident(BasePermission):
    """admin_ti y analista gestionan; jefe_area solo valida el cierre.

    Quién puede hacer qué exactamente lo afina IncidentUpdateSerializer.validate().
    """
    def has_permission(self, request, view):
        u = request.user
        return u.is_authenticated and u.role in ('admin_ti', 'analista', 'jefe_area')


class ReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in ('GET', 'HEAD', 'OPTIONS')
