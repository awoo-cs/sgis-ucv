from django.contrib import admin
from .models import Incident, IncidentStatusHistory, IncidentComment


class IncidentStatusHistoryInline(admin.TabularInline):
    model = IncidentStatusHistory
    extra = 0
    readonly_fields = ['previous_status', 'new_status', 'changed_by', 'changed_at', 'comment']
    can_delete = False


class IncidentCommentInline(admin.TabularInline):
    model = IncidentComment
    extra = 0
    readonly_fields = ['author', 'created_at']


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ['title', 'incident_type', 'criticality', 'status', 'affected_area', 'assigned_to', 'created_at']
    list_filter = ['incident_type', 'criticality', 'status', 'affected_area']
    search_fields = ['title', 'description', 'affected_area']
    inlines = [IncidentStatusHistoryInline, IncidentCommentInline]
    readonly_fields = ['created_at', 'updated_at', 'created_by']


@admin.register(IncidentStatusHistory)
class IncidentStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ['incident', 'previous_status', 'new_status', 'changed_by', 'changed_at']
    readonly_fields = ['incident', 'previous_status', 'new_status', 'changed_by', 'changed_at']
