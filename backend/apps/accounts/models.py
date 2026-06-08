from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    ADMIN_TI = 'admin_ti'
    ANALISTA = 'analista'
    JEFE_AREA = 'jefe_area'

    ROLE_CHOICES = [
        (ADMIN_TI, 'Administrador TI'),
        (ANALISTA, 'Analista de Seguridad'),
        (JEFE_AREA, 'Jefe de Área'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ANALISTA)

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_admin_ti(self):
        return self.role == self.ADMIN_TI

    @property
    def is_analista(self):
        return self.role == self.ANALISTA

    @property
    def is_jefe_area(self):
        return self.role == self.JEFE_AREA
