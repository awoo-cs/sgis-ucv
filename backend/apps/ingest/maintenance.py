"""Reinicio de la demo: borra SOLO lo generado por el sensor, deja intacto lo demás.

Sirve para repetir la demostración con el tablero en blanco sin perder los 45
incidentes de demo ni los registrados manualmente.
"""
from apps.incidents.models import Incident

from .models import SecurityEvent, BlockedIP, AlertThrottle


def reset_demo_data():
    """Borra eventos, bloqueos e incidentes automáticos del sensor. Devuelve conteos."""
    auto = Incident.objects.filter(created_by__username='sensor')
    counts = {
        'incidents': auto.count(),
        'events': SecurityEvent.objects.count(),
        'blocked': BlockedIP.objects.count(),
    }
    auto.delete()                      # cascada: historial, plan, blocked_ips (SET_NULL en events)
    SecurityEvent.objects.all().delete()
    BlockedIP.objects.all().delete()
    AlertThrottle.objects.all().delete()   # reinicia el agrupador de notificaciones
    return counts
