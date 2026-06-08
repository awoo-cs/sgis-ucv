from django.db import models


class ActionPlan(models.Model):
    incident = models.OneToOneField(
        'incidents.Incident',
        on_delete=models.CASCADE,
        related_name='action_plan'
    )
    steps = models.JSONField(default=list, verbose_name='Pasos del plan')
    is_customized = models.BooleanField(default=False, verbose_name='Editado por analista')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Plan de Acción'
        verbose_name_plural = 'Planes de Acción'

    def __str__(self):
        return f"Plan de acción — {self.incident}"
