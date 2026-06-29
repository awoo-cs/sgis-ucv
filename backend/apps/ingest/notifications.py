"""Notificación del playbook SOAR: avisa por email cuando se crea un incidente automático.

Best-effort por diseño: la notificación JAMÁS debe romper ni frenar la ingesta.
Por eso el envío real va en un hilo daemon y cualquier fallo se loguea, no se propaga.
"""
import logging
import threading

from django.conf import settings
from django.core.mail import send_mail
from django.db import connections, transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


def _window_seconds():
    """Tamaño de la ventana de agrupación (Opción A). Configurable; default 5 min."""
    return getattr(settings, 'SOAR_ALERT_WINDOW_SECONDS', 300)


def build_alert(incident, extra_count=0, extra_titles=''):
    """Devuelve (asunto, cuerpo) del correo de alerta para `incident`.

    Si `extra_count` > 0, añade al final un resumen de los incidentes que se
    contuvieron durante la ventana anterior y no se notificaron individualmente.
    """
    detected = incident.detected_at or incident.created_at
    subject = (
        f"[SGIS-UCV] Alerta de seguridad | {incident.get_criticality_display()} | "
        f"{incident.title}"
    )
    body = (
        f"Estimado encargado de seguridad:\n\n"
        f"El Sistema de Gestión de Incidentes de Seguridad (SGIS-UCV) ha detectado y "
        f"contenido automáticamente un incidente. Se remite el siguiente resumen para su "
        f"revisión.\n\n"
        f"Incidente:    #{incident.id}\n"
        f"Título:       {incident.title}\n"
        f"Tipo:         {incident.get_incident_type_display()}\n"
        f"Criticidad:   {incident.get_criticality_display()}\n"
        f"Sistema:      {incident.affected_system}\n"
        f"Detectado:    {detected:%Y-%m-%d %H:%M:%S}\n\n"
        f"Acción automática ejecutada: contención de la IP de origen conforme al "
        f"playbook de respuesta (SOAR).\n\n"
        f"Se solicita validar la contención y dar seguimiento al incidente desde el "
        f"Centro de Operaciones del SGIS-UCV.\n\n"
        f"Esta es una notificación automática; por favor, no responda a este correo.\n"
    )
    if extra_count:
        body += (
            f"\nAviso de actividad agrupada: durante la ventana de monitoreo anterior "
            f"se detectaron y contuvieron {extra_count} incidente(s) adicional(es), "
            f"que se resumen a continuación para no saturar su bandeja:\n\n{extra_titles}"
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


def notify_incident(incident):
    """Notificación agrupada (Opción A). Devuelve True si se envió un correo.

    El PRIMER incidente de una ventana se notifica al instante; los siguientes
    dentro de la misma ventana se acumulan (no envían correo). Cuando empieza una
    ventana nueva, el correo de ese incidente arrastra el resumen de los que
    quedaron en cola. Así el encargado recibe, como mucho, ~1 correo por ventana.

    El estado vive en BD (`AlertThrottle`, fila única) → consistente entre los
    workers de gunicorn. La decisión es atómica (`select_for_update`); el envío
    real (lento, SMTP) ocurre FUERA de la transacción para no retener el lock.
    """
    from .models import AlertThrottle  # import diferido: evita ciclos en el arranque

    now = timezone.now()
    window = _window_seconds()
    AlertThrottle.objects.get_or_create(pk=1)
    with transaction.atomic():
        state = AlertThrottle.objects.select_for_update().get(pk=1)
        fresh = (
            state.window_started_at is None
            or (now - state.window_started_at).total_seconds() >= window
        )
        if fresh:
            backlog, titles = state.suppressed, state.suppressed_titles
            state.window_started_at = now
            state.suppressed = 0
            state.suppressed_titles = ''
            state.save(update_fields=['window_started_at', 'suppressed', 'suppressed_titles'])
        else:
            state.suppressed += 1
            state.suppressed_titles += f"- Incidente #{incident.id}: {incident.title}\n"
            state.save(update_fields=['suppressed', 'suppressed_titles'])

    if not fresh:
        return False  # acumulado: irá en el resumen del próximo correo

    subject, body = build_alert(incident, extra_count=backlog, extra_titles=titles)
    send_mail(
        subject, body,
        settings.DEFAULT_FROM_EMAIL, [settings.SOAR_ALERT_EMAIL],
        fail_silently=False,
    )
    return True


def _safe(incident):
    try:
        notify_incident(incident)
    except Exception:  # noqa: BLE001 — best-effort: loguear, nunca romper la ingesta
        logger.exception("No se pudo enviar la alerta por email del incidente %s", incident.id)
    finally:
        connections.close_all()  # cerramos la conexión propia de este hilo daemon


def dispatch_incident_alert(incident):
    """Dispara el envío en un hilo daemon → no bloquea la respuesta del POST de ingesta."""
    threading.Thread(target=_safe, args=(incident,), daemon=True).start()
