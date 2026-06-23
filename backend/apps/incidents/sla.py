"""
SLA automático por criticidad (V1.1).

El profesor objetó que el encargado tuviera que digitar todo a mano. El SLA ya no
se escribe: se deriva de la criticidad del incidente y se calcula contra el
historial de estados. Cada incidente sabe solo cuánto tiempo le queda.
"""
from django.utils import timezone

# Presupuesto de atención (horas) según criticidad. Perilla de calibración.
SLA_HOURS = {'critico': 4, 'alto': 24, 'medio': 72, 'bajo': 168}
RISK_FRACTION = 0.2  # último 20% del plazo restante = "en riesgo"


def compute_sla(incident) -> dict:
    hours = SLA_HOURS.get(incident.criticality, 72)
    due_at = incident.detected_at + timezone.timedelta(hours=hours)

    # ¿Cuándo se atendió? Primer paso del historial hacia resuelto o cerrado.
    resolved_at = (
        incident.status_history
        .filter(new_status__in=['resuelto', 'cerrado'])
        .order_by('changed_at')
        .values_list('changed_at', flat=True)
        .first()
    )

    if resolved_at:
        status = 'cumplido' if resolved_at <= due_at else 'incumplido'
        remaining = None
    else:
        remaining = (due_at - timezone.now()).total_seconds()
        if remaining < 0:
            status = 'vencido'
        elif remaining <= hours * 3600 * RISK_FRACTION:
            status = 'en_riesgo'
        else:
            status = 'en_plazo'

    return {
        'hours': hours,
        'due_at': due_at.isoformat(),
        'status': status,
        'remaining_seconds': int(remaining) if remaining is not None else None,
    }
