"""Notificación del playbook SOAR: avisa por email cuando se crea un incidente automático.

Best-effort por diseño: la notificación JAMÁS debe romper ni frenar la ingesta.
Por eso el envío real va en un hilo daemon y cualquier fallo se loguea, no se propaga.
"""
import logging
import threading

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def build_alert(incident):
    """Devuelve (asunto, cuerpo) del correo de alerta para `incident`."""
    detected = incident.detected_at or incident.created_at
    subject = f"[SGIS-UCV] 🚨 {incident.get_criticality_display()} — {incident.title}"
    body = (
        f"El SGIS detectó y contuvo un incidente automáticamente.\n\n"
        f"Título:      {incident.title}\n"
        f"Tipo:        {incident.get_incident_type_display()}\n"
        f"Criticidad:  {incident.get_criticality_display()}\n"
        f"Sistema:     {incident.affected_system}\n"
        f"Detectado:   {detected:%Y-%m-%d %H:%M:%S}\n\n"
        f"Acción automática: contención de la IP atacante (playbook SOAR).\n"
        f"Revísalo en el Centro de Operaciones del SGIS-UCV.\n"
    )
    return subject, body


def send_incident_alert(incident):
    """Envía el correo de forma SÍNCRONA. Lanza si el backend de email falla."""
    subject, body = build_alert(incident)
    send_mail(
        subject, body,
        settings.DEFAULT_FROM_EMAIL, [settings.SOAR_ALERT_EMAIL],
        fail_silently=False,
    )


def _safe(incident):
    try:
        send_incident_alert(incident)
    except Exception:  # noqa: BLE001 — best-effort: loguear, nunca romper la ingesta
        logger.exception("No se pudo enviar la alerta por email del incidente %s", incident.id)


def dispatch_incident_alert(incident):
    """Dispara el envío en un hilo daemon → no bloquea la respuesta del POST de ingesta."""
    threading.Thread(target=_safe, args=(incident,), daemon=True).start()
