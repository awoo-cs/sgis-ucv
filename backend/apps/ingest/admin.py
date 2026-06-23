from django.contrib import admin
from .models import SecurityEvent


@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    list_display = ('received_at', 'source_ip', 'event_type', 'dest_port', 'is_alert', 'rule', 'sensor')
    list_filter = ('event_type', 'is_alert', 'rule', 'sensor')
    search_fields = ('source_ip', 'username', 'detail')
    readonly_fields = ('received_at',)
