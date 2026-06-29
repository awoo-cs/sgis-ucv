"""
Motor de reglas de detección del mini-SIEM (V1.1).

Propio, sin caja negra: tres reglas en Python plano que cualquiera puede leer.
Cada evento que entra por /api/ingest/events/ pasa por `evaluate()`. Si una regla
se cumple, se genera un incidente automático clasificado (reusando la misma
plantilla de planes de acción de la V1).

    atacante → sensor → /api/ingest/events/ → evaluate() → Incidente automático

Las constantes de abajo son las perillas de calibración: súbelas en producción,
bájalas para que la demo dispare rápido.
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.incidents.models import Incident, IncidentStatusHistory
from apps.action_plans.plan_templates import generate_action_plan
from .models import SecurityEvent, BlockedIP
from .notifications import dispatch_incident_alert

# ── Perillas de calibración ───────────────────────────────────────────
PORT_SCAN_PORTS = 8        # nº de puertos distintos…
PORT_SCAN_WINDOW = 30      # …en estos segundos = escaneo de puertos
BRUTE_FORCE_FAILS = 5      # nº de logins fallidos…
BRUTE_FORCE_WINDOW = 60    # …en estos segundos = fuerza bruta


def get_sensor_user():
    """Usuario de sistema 'sensor' que figura como autor de los incidentes auto-creados.

    Se crea una sola vez, sin contraseña usable (nadie inicia sesión con él).
    """
    User = get_user_model()
    user, created = User.objects.get_or_create(
        username='sensor',
        defaults={
            'first_name': 'Sensor', 'last_name': 'Automático',
            'email': 'sensor@sgis.local', 'role': User.ANALISTA, 'is_active': True,
        },
    )
    if created:
        user.set_unusable_password()
        user.save(update_fields=['password'])
    return user


def _blacklist():
    return set(getattr(settings, 'INGEST_BLACKLIST', []))


def evaluate(event: SecurityEvent):
    """Corre las 3 reglas sobre `event`. Devuelve dict con el resultado o None.

    El propio `event` ya está guardado, así que cuenta dentro de su ventana
    (es el evento Nº que cruza el umbral).
    """
    ip = event.source_ip
    now = timezone.now()

    # ── Regla 1: IP en lista negra (la más barata, va primero) ──────────
    if ip in _blacklist():
        return _fire(
            'blacklist_ip', event,
            incident_type=Incident.ACCESO_NO_AUTORIZADO, criticality=Incident.ALTO,
            title=f"Conexión desde IP en lista negra ({ip})",
            description=(
                f"El sensor «{event.sensor or 'desconocido'}» recibió tráfico desde "
                f"{ip}, una dirección presente en la lista negra de la organización. "
                f"Toda comunicación con esta IP se considera hostil por defecto."
            ),
        )

    # ── Regla 2: fuerza bruta (ráfaga de logins fallidos desde una IP) ──
    if event.event_type == SecurityEvent.AUTH_FAILURE:
        fails = SecurityEvent.objects.filter(
            source_ip=ip, event_type=SecurityEvent.AUTH_FAILURE,
            received_at__gte=now - timezone.timedelta(seconds=BRUTE_FORCE_WINDOW),
        ).count()
        if fails >= BRUTE_FORCE_FAILS:
            return _fire(
                'brute_force', event,
                incident_type=Incident.ACCESO_NO_AUTORIZADO, criticality=Incident.ALTO,
                title=f"Ataque de fuerza bruta desde {ip}",
                description=(
                    f"Se registraron {fails} intentos de autenticación fallidos desde "
                    f"{ip} en menos de {BRUTE_FORCE_WINDOW}s contra el sensor "
                    f"«{event.sensor or 'desconocido'}». Patrón típico de un ataque de "
                    f"fuerza bruta sobre credenciales."
                ),
            )

    # ── Regla 3: escaneo de puertos (una IP toca muchos puertos) ────────
    if event.event_type == SecurityEvent.CONNECTION:
        ports = SecurityEvent.objects.filter(
            source_ip=ip,
            received_at__gte=now - timezone.timedelta(seconds=PORT_SCAN_WINDOW),
        ).values('dest_port').distinct().count()
        if ports >= PORT_SCAN_PORTS:
            return _fire(
                'port_scan', event,
                incident_type=Incident.ACCESO_NO_AUTORIZADO, criticality=Incident.MEDIO,
                title=f"Escaneo de puertos detectado desde {ip}",
                description=(
                    f"La IP {ip} estableció conexiones a {ports} puertos distintos del "
                    f"sensor «{event.sensor or 'desconocido'}» en menos de "
                    f"{PORT_SCAN_WINDOW}s. Es el patrón de reconocimiento previo a un "
                    f"ataque dirigido."
                ),
            )

    return None


def _fire(rule, event, *, incident_type, criticality, title, description):
    """Marca el evento como alerta y crea (o reutiliza) el incidente del par (regla, IP)."""
    # Anti-duplicados: si ya hay un incidente ABIERTO/EN_INVESTIGACIÓN para esta
    # misma (regla, IP), no abrimos otro — engancha el evento al existente.
    incident = (
        Incident.objects
        .filter(
            status__in=[Incident.ABIERTO, Incident.EN_INVESTIGACION],
            events__rule=rule, events__source_ip=event.source_ip,
        )
        .distinct()
        .first()
    )
    created = incident is None
    if created:
        sensor_user = get_sensor_user()
        incident = Incident.objects.create(
            title=title,
            description=description,
            incident_type=incident_type,
            criticality=criticality,
            status=Incident.ABIERTO,
            affected_area='Perímetro de red',
            affected_system=event.sensor or 'Sensor SGIS',
            detected_at=event.received_at,
            created_by=sensor_user,
        )
        IncidentStatusHistory.objects.create(
            incident=incident, previous_status='', new_status=Incident.ABIERTO,
            changed_by=sensor_user,
            comment=f"Incidente generado automáticamente por el motor de detección (regla: {rule}).",
        )
        generate_action_plan(incident)  # RF6: mismo plan automático que la V1
        dispatch_incident_alert(incident)  # Playbook SOAR: notifica al equipo por email (async)

    # ── Contención automática (V1.2 SOAR): bloquear la IP atacante ──────
    # No basta detectar: el sistema ACTÚA. Metemos la IP en la lista de bloqueo
    # que el sensor consulta y aplica; la conexión del atacante se corta en vivo.
    blocked = _contain(event.source_ip, rule, incident, reason=title)
    if created:
        # Sella en el bloqueo que la alerta salió → el tablero pinta "Notificar ✓".
        BlockedIP.objects.filter(source_ip=event.source_ip).update(alerted_at=timezone.now())

    event.is_alert = True
    event.rule = rule
    event.triggered_incident = incident
    event.save(update_fields=['is_alert', 'rule', 'triggered_incident'])

    return {
        'rule': rule, 'incident_id': incident.id,
        'incident_created': created, 'blocked_ip': blocked,
    }


def _contain(ip, rule, incident, *, reason):
    """Da de alta (o reactiva) el bloqueo de `ip`. Idempotente. Devuelve la IP o None."""
    obj, created = BlockedIP.objects.get_or_create(
        source_ip=ip,
        defaults={'rule': rule, 'reason': reason[:255], 'incident': incident, 'active': True},
    )
    if not created and not obj.active:
        obj.active = True
        obj.released_at = None
        obj.save(update_fields=['active', 'released_at'])
        created = True  # se volvió a contener → vale la pena anotarlo

    if created:
        IncidentStatusHistory.objects.create(
            incident=incident, previous_status=incident.status, new_status=incident.status,
            changed_by=get_sensor_user(),
            comment=f"Contención automática (SOAR): IP {ip} bloqueada en el perímetro.",
        )
    return ip
