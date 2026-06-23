"""Convierte los pasos de texto plano (V1) a checklist con evidencia (V1.1)."""
from django.db import migrations


def to_checklist(apps, schema_editor):
    ActionPlan = apps.get_model('action_plans', 'ActionPlan')
    for plan in ActionPlan.objects.all():
        steps = plan.steps or []
        if steps and isinstance(steps[0], str):
            plan.steps = [
                {'text': s, 'done': False, 'done_by': None, 'done_at': None, 'evidence': ''}
                for s in steps
            ]
            plan.save(update_fields=['steps'])


def to_text(apps, schema_editor):
    ActionPlan = apps.get_model('action_plans', 'ActionPlan')
    for plan in ActionPlan.objects.all():
        steps = plan.steps or []
        if steps and isinstance(steps[0], dict):
            plan.steps = [s.get('text', '') for s in steps]
            plan.save(update_fields=['steps'])


class Migration(migrations.Migration):
    dependencies = [('action_plans', '0001_initial')]
    operations = [migrations.RunPython(to_checklist, to_text)]
