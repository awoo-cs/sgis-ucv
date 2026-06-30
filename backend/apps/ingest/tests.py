"""
Prueba del motor de reglas. Ejecutar:

    docker compose exec backend python manage.py test apps.ingest
"""
from datetime import timedelta
from unittest import mock

from django.core import mail
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import CustomUser
from apps.incidents.models import Incident
from .detection import evaluate, get_sensor_user
from .maintenance import reset_demo_data
from .models import SecurityEvent, BlockedIP, AlertThrottle
from .notifications import build_alert, send_incident_alert, notify_incident


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

    def test_detection_contains_attacker_ip(self):
        """SOAR: al disparar una regla, la IP atacante queda en contención activa."""
        result = None
        for port in range(8000, 8008):
            _, result = _event(event_type=SecurityEvent.CONNECTION, dest_port=port)
        self.assertEqual(result['blocked_ip'], '10.0.0.5')
        self.assertTrue(BlockedIP.objects.filter(source_ip='10.0.0.5', active=True).exists())

    def test_quiet_traffic_blocks_nobody(self):
        for port in range(8000, 8003):
            _event(event_type=SecurityEvent.CONNECTION, dest_port=port)
        self.assertEqual(BlockedIP.objects.count(), 0)


@override_settings(
    INGEST_BLACKLIST=[],
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    DEFAULT_FROM_EMAIL='SGIS-UCV <no-reply@sgis.local>',
    SOAR_ALERT_EMAIL='leopb77@gmail.com',
)
class NotificationTests(TestCase):
    """Playbook SOAR — beat «Notificar»: el incidente automático avisa por email."""

    def _make_incident(self):
        return Incident.objects.create(
            title='Escaneo de puertos detectado desde 10.0.0.5',
            description='Prueba de notificación.',
            incident_type=Incident.ACCESO_NO_AUTORIZADO,
            criticality=Incident.MEDIO,
            status=Incident.ABIERTO,
            affected_area='Perímetro de red',
            affected_system='sensor-test',
            detected_at=timezone.now(),
            created_by=get_sensor_user(),
        )

    def test_alert_email_goes_to_the_soar_inbox(self):
        send_incident_alert(self._make_incident())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['leopb77@gmail.com'])

    def test_alert_subject_and_body_carry_the_essentials(self):
        incident = self._make_incident()
        subject, body = build_alert(incident)
        self.assertIn(incident.get_criticality_display(), subject)
        self.assertIn(incident.title, subject)
        self.assertIn('contención', body.lower())

    def test_new_incident_dispatches_exactly_one_alert(self):
        with mock.patch('apps.ingest.detection.dispatch_incident_alert') as dispatch:
            for port in range(8000, 8008):
                _event(event_type=SecurityEvent.CONNECTION, dest_port=port)
        self.assertEqual(dispatch.call_count, 1)

    def test_dedup_does_not_renotify(self):
        with mock.patch('apps.ingest.detection.dispatch_incident_alert') as dispatch:
            for port in range(8000, 8016):  # 8 disparan; los 8 siguientes son dedup
                _event(event_type=SecurityEvent.CONNECTION, dest_port=port)
        self.assertEqual(dispatch.call_count, 1)

    def test_containment_records_when_it_alerted(self):
        for port in range(8000, 8008):
            _event(event_type=SecurityEvent.CONNECTION, dest_port=port)
        block = BlockedIP.objects.get(source_ip='10.0.0.5')
        self.assertIsNotNone(block.alerted_at)


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    DEFAULT_FROM_EMAIL='SGIS-UCV <no-reply@sgis.local>',
    SOAR_ALERT_EMAIL='leopb77@gmail.com',
    SOAR_ALERT_WINDOW_SECONDS=300,
)
class ThrottleTests(TestCase):
    """Opción A — resumen por ventana: no inundar al encargado con muchos correos."""

    def setUp(self):
        # Los tests que lanzan el hilo daemon de detección pueden dejar una fila
        # AlertThrottle comprometida fuera de la transacción; partimos de cero.
        AlertThrottle.objects.all().delete()
        mail.outbox.clear()

    def _incident(self, n):
        return Incident.objects.create(
            title=f'Incidente automático #{n}',
            description='x', incident_type=Incident.ACCESO_NO_AUTORIZADO,
            criticality=Incident.MEDIO, status=Incident.ABIERTO,
            affected_area='Red', affected_system='sensor-test',
            detected_at=timezone.now(), created_by=get_sensor_user(),
        )

    def test_first_incident_notifies_immediately(self):
        self.assertTrue(notify_incident(self._incident(1)))
        self.assertEqual(len(mail.outbox), 1)

    def test_burst_within_window_is_suppressed(self):
        notify_incident(self._incident(1))            # envía
        notify_incident(self._incident(2))            # se acumula
        notify_incident(self._incident(3))            # se acumula
        self.assertEqual(len(mail.outbox), 1)         # 1 solo correo, no 3
        self.assertEqual(AlertThrottle.objects.get(pk=1).suppressed, 2)

    def test_next_window_sends_summary_of_suppressed(self):
        notify_incident(self._incident(1))            # envía, abre ventana
        notify_incident(self._incident(2))            # se acumula (1 en cola)
        # Simulo que pasó la ventana retrasando su inicio:
        st = AlertThrottle.objects.get(pk=1)
        st.window_started_at = timezone.now() - timedelta(seconds=301)
        st.save(update_fields=['window_started_at'])
        self.assertTrue(notify_incident(self._incident(3)))
        self.assertEqual(len(mail.outbox), 2)         # 2º correo (resumen + nuevo)
        self.assertIn('1 incidente', mail.outbox[1].body)   # menciona el acumulado
        self.assertEqual(AlertThrottle.objects.get(pk=1).suppressed, 0)  # cola vaciada


@override_settings(INGEST_BLACKLIST=[])
class ReleaseTests(TestCase):
    """Liberar contención (human-in-the-loop): analista/admin sí; jefe_area no."""

    URL = '/api/ingest/blocklist/10.0.0.5/release/'

    def setUp(self):
        self.client = APIClient()
        for port in range(8000, 8008):  # genera una IP contenida
            _event(event_type=SecurityEvent.CONNECTION, dest_port=port)
        self.assertTrue(BlockedIP.objects.filter(source_ip='10.0.0.5', active=True).exists())

    def test_analista_release_deactivates_block(self):
        ana = CustomUser.objects.create_user(username='ana', password='x', role=CustomUser.ANALISTA)
        self.client.force_authenticate(ana)
        res = self.client.post(self.URL)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['released'], '10.0.0.5')
        block = BlockedIP.objects.get(source_ip='10.0.0.5')
        self.assertFalse(block.active)
        self.assertIsNotNone(block.released_at)
        # y desaparece de la blocklist activa que consulta el sensor
        self.assertFalse(BlockedIP.objects.filter(active=True).exists())

    def test_jefe_area_cannot_release(self):
        jefe = CustomUser.objects.create_user(username='jefe', password='x', role=CustomUser.JEFE_AREA)
        self.client.force_authenticate(jefe)
        res = self.client.post(self.URL)
        self.assertEqual(res.status_code, 403)
        self.assertTrue(BlockedIP.objects.filter(source_ip='10.0.0.5', active=True).exists())


@override_settings(INGEST_BLACKLIST=[])
class ResetTests(TestCase):
    """Reiniciar la demo: borra lo del sensor, conserva lo registrado a mano."""

    def test_reset_clears_sensor_data_keeps_manual(self):
        author = CustomUser.objects.create_user(
            username='analista_manual', password='x', role=CustomUser.ANALISTA)
        manual = Incident.objects.create(
            title='Incidente registrado a mano',
            description='No lo creó el sensor.',
            incident_type=Incident.ACCESO_NO_AUTORIZADO,
            criticality=Incident.MEDIO,
            status=Incident.ABIERTO,
            affected_area='Mesa de ayuda',
            affected_system='Correo',
            detected_at=timezone.now(),
            created_by=author,
        )
        for port in range(8000, 8008):  # incidente + evento + bloqueo del sensor
            _event(event_type=SecurityEvent.CONNECTION, dest_port=port)
        self.assertTrue(Incident.objects.filter(created_by__username='sensor').exists())

        counts = reset_demo_data()

        self.assertFalse(Incident.objects.filter(created_by__username='sensor').exists())
        self.assertTrue(Incident.objects.filter(pk=manual.pk).exists())
        self.assertEqual(SecurityEvent.objects.count(), 0)
        self.assertEqual(BlockedIP.objects.count(), 0)
        self.assertEqual(counts['incidents'], 1)

    def test_reset_endpoint_requires_admin_ti(self):
        ana = CustomUser.objects.create_user(username='ana2', password='x', role=CustomUser.ANALISTA)
        client = APIClient()
        client.force_authenticate(ana)
        res = client.post('/api/ingest/reset/')
        self.assertEqual(res.status_code, 403)


class IPv4EmailBackendTests(TestCase):
    """El backend debe resolver el servidor SMTP solo por IPv4 (fix Railway)."""

    def test_open_forces_ipv4_resolution(self):
        from django.core.mail.backends.smtp import EmailBackend as SMTPBackend
        from .ipv4_email import IPv4EmailBackend
        import socket

        captured = {}

        def fake_super_open(self):
            # Mientras open() corre, getaddrinfo debe entregar solo IPv4.
            res = socket.getaddrinfo('localhost', 80)
            captured['families'] = {r[0] for r in res}
            return True

        with mock.patch.object(SMTPBackend, 'open', fake_super_open):
            IPv4EmailBackend().open()

        self.assertEqual(captured['families'], {socket.AF_INET})
        # Y fuera de open(), getaddrinfo queda restaurado (puede volver a dar IPv6).
        self.assertIs(socket.getaddrinfo, socket.getaddrinfo)
