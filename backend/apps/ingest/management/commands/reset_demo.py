from django.core.management.base import BaseCommand

from apps.ingest.maintenance import reset_demo_data


class Command(BaseCommand):
    help = 'Borra eventos, bloqueos e incidentes automáticos del sensor (deja demo/manuales).'

    def handle(self, *args, **opts):
        c = reset_demo_data()
        self.stdout.write(self.style.SUCCESS(
            f"Reset: {c['incidents']} incidentes, {c['events']} eventos, {c['blocked']} bloqueos."
        ))
