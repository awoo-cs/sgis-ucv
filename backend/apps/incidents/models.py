from django.db import models
from django.conf import settings


class Incident(models.Model):
    # Tipos de incidente (RF3)
    MALWARE = 'malware'
    ACCESO_NO_AUTORIZADO = 'acceso_no_autorizado'
    PHISHING = 'phishing'
    FUGA_DATOS = 'fuga_datos'
    FALLO_CONFIGURACION = 'fallo_configuracion'
    OTRO = 'otro'

    TYPE_CHOICES = [
        (MALWARE, 'Malware'),
        (ACCESO_NO_AUTORIZADO, 'Acceso no autorizado'),
        (PHISHING, 'Phishing'),
        (FUGA_DATOS, 'Fuga de datos'),
        (FALLO_CONFIGURACION, 'Fallo de configuración'),
        (OTRO, 'Otro'),
    ]

    # Niveles de criticidad (RF3)
    BAJO = 'bajo'
    MEDIO = 'medio'
    ALTO = 'alto'
    CRITICO = 'critico'

    CRITICALITY_CHOICES = [
        (BAJO, 'Bajo'),
        (MEDIO, 'Medio'),
        (ALTO, 'Alto'),
        (CRITICO, 'Crítico'),
    ]

    # Estados del ciclo de vida (RF5)
    ABIERTO = 'abierto'
    EN_INVESTIGACION = 'en_investigacion'
    RESUELTO = 'resuelto'
    CERRADO = 'cerrado'

    STATUS_CHOICES = [
        (ABIERTO, 'Abierto'),
        (EN_INVESTIGACION, 'En Investigación'),
        (RESUELTO, 'Resuelto'),
        (CERRADO, 'Cerrado'),
    ]

    title = models.CharField(max_length=200, verbose_name='Título')
    description = models.TextField(verbose_name='Descripción')
    incident_type = models.CharField(max_length=30, choices=TYPE_CHOICES, verbose_name='Tipo')
    criticality = models.CharField(max_length=10, choices=CRITICALITY_CHOICES, verbose_name='Criticidad')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=ABIERTO, verbose_name='Estado')
    affected_area = models.CharField(max_length=100, verbose_name='Área afectada')
    affected_system = models.CharField(max_length=100, blank=True, verbose_name='Sistema/Equipo involucrado')
    detected_at = models.DateTimeField(verbose_name='Fecha y hora de detección')
    deadline = models.DateField(null=True, blank=True, verbose_name='Fecha límite de atención')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_incidents',
        verbose_name='Registrado por'
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='assigned_incidents',
        verbose_name='Responsable asignado'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Incidente'
        verbose_name_plural = 'Incidentes'

    def __str__(self):
        return f"[{self.get_criticality_display()}] {self.title}"

    @property
    def is_closed(self):
        return self.status == self.CERRADO


class IncidentStatusHistory(models.Model):
    """Registro inmutable de cambios de estado (RF5, RNF8)."""
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='status_history')
    previous_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    changed_at = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(blank=True)

    class Meta:
        ordering = ['changed_at']
        verbose_name = 'Historial de estado'
        verbose_name_plural = 'Historial de estados'

    def __str__(self):
        return f"{self.incident} | {self.previous_status} → {self.new_status}"


class IncidentComment(models.Model):
    """Comentarios adicionales — no modifica el historial inmutable (RNF8)."""
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Comentario'
        verbose_name_plural = 'Comentarios'
