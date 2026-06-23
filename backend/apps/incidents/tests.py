"""
SLA automático + workflow de cierre por rol (V1.1). Ejecutar:

    docker compose exec backend python manage.py test apps.incidents
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import Incident, IncidentStatusHistory
from .sla import compute_sla

User = get_user_model()


def _incident(**kw):
    kw.setdefault('title', 'Prueba')
    kw.setdefault('description', '...')
    kw.setdefault('incident_type', 'malware')
    kw.setdefault('criticality', 'critico')
    kw.setdefault('affected_area', 'Centro de Datos')
    kw.setdefault('detected_at', timezone.now())
    return Incident.objects.create(**kw)


class SLATests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='ana', role='analista')

    def test_open_critical_is_en_plazo(self):
        inc = _incident(created_by=self.user)  # crítico = 4h, recién detectado
        sla = compute_sla(inc)
        self.assertEqual(sla['hours'], 4)
        self.assertEqual(sla['status'], 'en_plazo')
        self.assertGreater(sla['remaining_seconds'], 0)

    def test_open_overdue_is_vencido(self):
        inc = _incident(created_by=self.user, detected_at=timezone.now() - timezone.timedelta(hours=10))
        self.assertEqual(compute_sla(inc)['status'], 'vencido')

    def test_resolved_on_time_is_cumplido(self):
        inc = _incident(created_by=self.user, status='resuelto')
        IncidentStatusHistory.objects.create(
            incident=inc, previous_status='en_investigacion', new_status='resuelto',
            changed_by=self.user,  # changed_at = ahora, dentro de las 4h
        )
        sla = compute_sla(inc)
        self.assertEqual(sla['status'], 'cumplido')
        self.assertIsNone(sla['remaining_seconds'])


class ClosureWorkflowTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create(username='admin', role='admin_ti')
        cls.analista = User.objects.create(username='ana', role='analista')
        cls.jefe = User.objects.create(username='jefe', role='jefe_area')

    def _resolved_incident(self):
        return _incident(created_by=self.admin, status='resuelto', criticality='alto')

    def _patch(self, who, inc, payload):
        self.client.force_authenticate(who)
        return self.client.patch(f'/api/incidents/{inc.id}/', payload, format='json')

    def test_analista_cannot_close(self):
        inc = self._resolved_incident()
        r = self._patch(self.analista, inc, {'new_status': 'cerrado', 'status_comment': 'x'})
        self.assertEqual(r.status_code, 400)
        inc.refresh_from_db()
        self.assertEqual(inc.status, 'resuelto')

    def test_jefe_can_validate_close(self):
        inc = self._resolved_incident()
        r = self._patch(self.jefe, inc, {'new_status': 'cerrado', 'status_comment': 'validado'})
        self.assertEqual(r.status_code, 200)
        inc.refresh_from_db()
        self.assertEqual(inc.status, 'cerrado')

    def test_jefe_cannot_edit_fields(self):
        inc = self._resolved_incident()
        r = self._patch(self.jefe, inc, {'title': 'manipulado'})
        self.assertEqual(r.status_code, 400)
        inc.refresh_from_db()
        self.assertEqual(inc.title, 'Prueba')

    def test_cannot_close_unless_resolved(self):
        inc = _incident(created_by=self.admin, status='abierto')
        r = self._patch(self.admin, inc, {'new_status': 'cerrado'})
        self.assertEqual(r.status_code, 400)
