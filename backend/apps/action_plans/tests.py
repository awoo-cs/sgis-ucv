"""
Checklist del plan de acción: marcar un paso sella quién y cuándo (V1.1).

    docker compose exec backend python manage.py test apps.action_plans
"""
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.incidents.models import Incident
from .plan_templates import generate_action_plan

User = get_user_model()


class ActionPlanChecklistTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create(username='admin', role='admin_ti', first_name='Admin', last_name='TI')
        cls.inc = Incident.objects.create(
            title='x', description='x', incident_type='malware', criticality='alto',
            affected_area='x', detected_at=timezone.now(), created_by=cls.admin,
        )
        generate_action_plan(cls.inc)

    def test_steps_start_as_checklist_dicts(self):
        plan = self.inc.action_plan
        self.assertTrue(plan.steps and isinstance(plan.steps[0], dict))
        self.assertFalse(plan.steps[0]['done'])

    def test_checking_step_stamps_user_and_progress(self):
        plan = self.inc.action_plan
        steps = plan.steps
        steps[0]['done'] = True
        steps[0]['evidence'] = 'Equipo aislado, captura en ticket #4421'
        self.client.force_authenticate(self.admin)
        r = self.client.patch(f'/api/action-plans/{plan.id}/', {'steps': steps}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['progress']['done'], 1)
        plan.refresh_from_db()
        self.assertTrue(plan.steps[0]['done'])
        self.assertEqual(plan.steps[0]['done_by'], 'Admin TI')   # se selló quién
        self.assertTrue(plan.steps[0]['done_at'])                # y cuándo
        self.assertIn('4421', plan.steps[0]['evidence'])

    def test_unchecking_clears_stamp(self):
        plan = self.inc.action_plan
        steps = plan.steps
        steps[0]['done'] = True
        self.client.force_authenticate(self.admin)
        self.client.patch(f'/api/action-plans/{plan.id}/', {'steps': steps}, format='json')
        steps = self.inc.action_plan.steps
        steps[0]['done'] = False
        r = self.client.patch(f'/api/action-plans/{plan.id}/', {'steps': steps}, format='json')
        self.assertEqual(r.data['progress']['done'], 0)
        plan.refresh_from_db()
        self.assertFalse(plan.steps[0]['done'])
        self.assertIsNone(plan.steps[0]['done_by'])
