from django.db import models


class SecurityEvent(models.Model):
    """
    Evento crudo reportado por un sensor (V1.1).

    Es la materia prima del mini-SIEM: el sensor observa conexiones e intentos
    de login contra sí mismo y los envía aquí. El motor de reglas (detection.py)
    los evalúa y, si procede, genera un incidente automático.
    """
    CONNECTION = 'connection'        # intento de conexión TCP a un puerto
    AUTH_FAILURE = 'auth_failure'    # intento de login fallido
    AUTH_SUCCESS = 'auth_success'    # login correcto (informativo)
    OTHER = 'other'

    TYPE_CHOICES = [
        (CONNECTION, 'Conexión'),
        (AUTH_FAILURE, 'Login fallido'),
        (AUTH_SUCCESS, 'Login correcto'),
        (OTHER, 'Otro'),
    ]

    received_at = models.DateTimeField(auto_now_add=True, db_index=True)
    event_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=OTHER)
    source_ip = models.GenericIPAddressField(verbose_name='IP de origen')
    dest_port = models.PositiveIntegerField(null=True, blank=True, verbose_name='Puerto destino')
    username = models.CharField(max_length=150, blank=True)
    detail = models.CharField(max_length=255, blank=True)
    sensor = models.CharField(max_length=100, blank=True, verbose_name='Sensor que reportó')
    raw = models.JSONField(default=dict, blank=True)

    # Resultado de la evaluación del motor de reglas
    is_alert = models.BooleanField(default=False, verbose_name='Disparó una regla')
    rule = models.CharField(max_length=40, blank=True, verbose_name='Regla disparada')
    triggered_incident = models.ForeignKey(
        'incidents.Incident',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='events',
        verbose_name='Incidente generado',
    )

    class Meta:
        ordering = ['-received_at']
        verbose_name = 'Evento de seguridad'
        verbose_name_plural = 'Eventos de seguridad'
        indexes = [
            # El motor consulta ventanas deslizantes por IP de origen.
            models.Index(fields=['source_ip', 'received_at']),
        ]

    def __str__(self):
        port = f":{self.dest_port}" if self.dest_port else ''
        return f"{self.source_ip}{port} [{self.event_type}]"


class BlockedIP(models.Model):
    """
    IP en contención automática (V1.2 — salto SIEM→SOAR).

    Cuando una regla dispara, el motor no solo crea el incidente: además mete la
    IP atacante aquí. El sensor consulta esta lista (GET /api/ingest/blocklist/)
    y corta toda conexión entrante desde una IP activa → contención en vivo.

    Es la "lista de bloqueo" que un firewall real aplicaría; aquí la aplica el
    propio sensor para poder demostrarlo sobre la LAN del salón sin tocar el
    firewall físico.
    """
    source_ip = models.GenericIPAddressField(unique=True, verbose_name='IP bloqueada')
    rule = models.CharField(max_length=40, verbose_name='Regla que la disparó')
    reason = models.CharField(max_length=255, blank=True)
    incident = models.ForeignKey(
        'incidents.Incident', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='blocked_ips', verbose_name='Incidente que la originó',
    )
    active = models.BooleanField(default=True, verbose_name='Bloqueo activo')
    created_at = models.DateTimeField(auto_now_add=True)
    released_at = models.DateTimeField(null=True, blank=True, verbose_name='Liberada el')
    alerted_at = models.DateTimeField(null=True, blank=True, verbose_name='Notificado el')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'IP bloqueada'
        verbose_name_plural = 'IPs bloqueadas'

    def __str__(self):
        return f"{self.source_ip} ({'activa' if self.active else 'liberada'})"
