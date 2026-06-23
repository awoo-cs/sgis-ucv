"""
Prueba del motor de reglas. Ejecutar:

    docker compose exec backend python manage.py test apps.ingest
"""
from django.test import TestCase
from django.test.utils import override_settings

from apps.incidents.models import Incident
from .detection import evaluate
from .models import SecurityEvent


def _event(**kw):
    kw.setdefault('source_ip', '10.0.0.5')
    kw.setdefault('sensor', 'sensor-test')
    ev = SecurityEvent.objects.create(**kw)
    return ev, evaluate(ev)


@override_settings(INGEST_BLACKLIST=['203.0.113.66'])
class DetectionEngineTests(TestCase):

    def test_port_scan_creates_incident(self):
        result = None
        for port in range(8000, 8008):  # 8 puertos distintos
            _, result = _event(event_type=SecurityEvent.CONNECTION, dest_port=port)
        self.assertIsNotNone(result, 'el 8º puerto debió disparar la regla')
        self.assertEqual(result['rule'], 'port_scan')
        self.assertEqual(Incident.objects.count(), 1)

    def test_brute_force_creates_incident(self):
        result = None
        for _ in range(5):  # 5 logins fallidos
            _, result = _event(event_type=SecurityEvent.AUTH_FAILURE, dest_port=22)
        self.assertEqual(result['rule'], 'brute_force')
        self.assertEqual(Incident.objects.count(), 1)

    def test_blacklist_fires_on_first_event(self):
        _, result = _event(event_type=SecurityEvent.CONNECTION, source_ip='203.0.113.66', dest_port=80)
        self.assertEqual(result['rule'], 'blacklist_ip')
        self.assertEqual(Incident.objects.count(), 1)

    def test_dedup_does_not_duplicate_incident(self):
        for port in range(8000, 8008):
            _event(event_type=SecurityEvent.CONNECTION, dest_port=port)
        self.assertEqual(Incident.objects.count(), 1)
        # Más eventos del mismo (regla, IP) mientras el incidente sigue abierto: no abre otro.
        for port in range(8008, 8016):
            _event(event_type=SecurityEvent.CONNECTION, dest_port=port)
        self.assertEqual(Incident.objects.count(), 1)

    def test_quiet_traffic_creates_nothing(self):
        for port in range(8000, 8003):  # solo 3 puertos, bajo el umbral
            _, result = _event(event_type=SecurityEvent.CONNECTION, dest_port=port)
            self.assertIsNone(result)
        self.assertEqual(Incident.objects.count(), 0)
