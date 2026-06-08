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


class ReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in ('GET', 'HEAD', 'OPTIONS')
