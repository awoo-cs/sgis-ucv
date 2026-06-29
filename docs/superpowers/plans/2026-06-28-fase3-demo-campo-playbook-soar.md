# Fase 3 — Demo de Campo: Playbook SOAR + Kit — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convertir la contención de una sola acción en un playbook SOAR (Detectar → Contener → **Notificar por email** → Documentar → **Revisar/Liberar**), con `Reiniciar demo` para repetir, **firewall real** en el sensor, y un **launcher PowerShell** que despliega cada rol en su laptop.

**Architecture:** Se extiende `apps/ingest` (modelo `BlockedIP` + `detection._fire/_contain`) — NO se introduce `ResponseAction`. El email se dispara en un hilo daemon para no bloquear la ingesta. La liberación es declarativa (sale de `BlockedIP.active=True` → el sensor reconcilia en ≤2s). El firewall real lo aplica el sensor con `netsh` (best-effort, fallback a corte app). El launcher es una GUI WinForms nativa de Windows PowerShell 5.1.

**Tech Stack:** Django 4.2 + DRF, Django email (SMTP/console), Vue 3 + Vuetify, PowerShell 5.1 WinForms, Python stdlib (sensor).

**Spec:** `docs/superpowers/specs/2026-06-28-fase3-demo-campo-playbook-soar-design.md`

**Cómo correr los tests del backend:** el backend corre en Docker.
```bash
docker compose exec backend python manage.py test apps.ingest -v 2
```
(Si `docker compose ps` no muestra el backend arriba: `docker compose up -d backend db`.)

**Commits:** sin `Co-Authored-By: Claude`. Rama `dev`. Commitear al final de cada Task.

---

## File Structure

**Backend (`backend/apps/ingest/`):**
- Create `notifications.py` — armado y envío del email de alerta (sync + dispatch en hilo).
- Create `maintenance.py` — `reset_demo_data()` (borra solo lo del sensor).
- Create `management/commands/reset_demo.py` — comando CLI.
- Create `migrations/0003_blockedip_alerted_at.py` — campo `alerted_at`.
- Modify `models.py` — `BlockedIP.alerted_at`.
- Modify `detection.py` — engancha `dispatch_incident_alert` en `_fire` (solo incidente nuevo); setea `alerted_at`.
- Modify `views.py` — `ReleaseBlockView`, `ResetDemoView`.
- Modify `urls.py` — rutas `blocklist/<ip>/release/`, `reset/`.
- Modify `serializers.py` — `BlockedIPSerializer` expone `alerted_at`, `incident`, `created_at`.
- Modify `tests.py` — tests de notificar / liberar / reiniciar.
- Modify `backend/sgis/settings/base.py` — config de email + `SOAR_ALERT_EMAIL`.

**Sensor (`tools/`):**
- Modify `sensor.py` — `diff_blocklist()` puro + `netsh` add/delete + flag `--firewall` + admin check + limpieza.

**Frontend (`frontend/src/`):**
- Modify `views/OperationsView.vue` — pasos del playbook por IP + botón Liberar + botón Reiniciar.
- Modify `stores/incidents.js` — `releaseBlock(ip)`, `resetDemo()`.

**Kit (`tools/`):**
- Create `Launcher.ps1`, `Iniciar.bat`, `LEEME.txt`.
- Modify `README.md` — runbook de los 7 beats.

---

## Task 1: Email de alerta (paso "Notificar")

**Files:**
- Create: `backend/apps/ingest/notifications.py`
- Modify: `backend/sgis/settings/base.py` (añadir bloque de email al final)
- Modify: `backend/apps/ingest/detection.py` (`_fire`)
- Test: `backend/apps/ingest/tests.py`

- [ ] **Step 1: Settings de email**

Añadir al final de `base.py`:
```python
# ── Email / notificaciones SOAR ───────────────────────────────────────
# Dev: backend de consola (imprime el correo en el log, sin SMTP real).
# Demo (Railway): EMAIL_BACKEND=...smtp.EmailBackend + credenciales SMTP.
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='SGIS-UCV <no-reply@sgis.local>')
# Destinatario de las alertas automáticas del playbook SOAR.
SOAR_ALERT_EMAIL = config('SOAR_ALERT_EMAIL', default='leopb77@gmail.com')
```

- [ ] **Step 2: Write `notifications.py`**

```python
"""Notificación del playbook SOAR: avisa por email cuando se crea un incidente automático.

Best-effort por diseño: la notificación JAMÁS debe romper ni frenar la ingesta.
Por eso el envío real va en un hilo daemon y cualquier fallo se loguea, no se propaga.
"""
import logging
import threading

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def build_alert(incident):
    """Devuelve (asunto, cuerpo) del correo de alerta para `incident`."""
    subject = f"[SGIS-UCV] \U0001F6A8 {incident.get_criticality_display()} — {incident.title}"
    body = (
        f"El SGIS detectó y contuvo un incidente automáticamente.\n\n"
        f"Título:      {incident.title}\n"
        f"Tipo:        {incident.get_incident_type_display()}\n"
        f"Criticidad:  {incident.get_criticality_display()}\n"
        f"Sistema:     {incident.affected_system}\n"
        f"Detectado:   {incident.detected_at:%Y-%m-%d %H:%M:%S}\n\n"
        f"Acción automática: contención de la IP atacante (playbook SOAR).\n"
        f"Revísalo en el Centro de Operaciones del SGIS-UCV.\n"
    )
    return subject, body


def send_incident_alert(incident):
    """Envía el correo de forma SÍNCRONA. Lanza si el backend de email falla."""
    subject, body = build_alert(incident)
    send_mail(
        subject, body,
        settings.DEFAULT_FROM_EMAIL, [settings.SOAR_ALERT_EMAIL],
        fail_silently=False,
    )


def _safe(incident):
    try:
        send_incident_alert(incident)
    except Exception:                       # noqa: BLE001 — best-effort, no romper la ingesta
        logger.exception("No se pudo enviar la alerta por email del incidente %s", incident.id)


def dispatch_incident_alert(incident):
    """Dispara el envío en un hilo daemon → no bloquea la respuesta del POST de ingesta."""
    threading.Thread(target=_safe, args=(incident,), daemon=True).start()
```

- [ ] **Step 3: Write the failing tests**

Añadir a `tests.py` (importar arriba: `from django.core import mail` y `from unittest import mock`):
```python
@override_settings(
    INGEST_BLACKLIST=['203.0.113.66'],
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    SOAR_ALERT_EMAIL='leopb77@gmail.com',
)
class NotificationTests(TestCase):

    def test_send_incident_alert_emails_the_soar_inbox(self):
        from .notifications import send_incident_alert
        inc = Incident.objects.create(
            title='Prueba', description='x', incident_type=Incident.ACCESO_NO_AUTORIZADO,
            criticality=Incident.ALTO, status=Incident.ABIERTO, affected_area='X',
            created_by=get_sensor_user(),
        )
        send_incident_alert(inc)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['leopb77@gmail.com'])
        self.assertIn('Prueba', mail.outbox[0].subject)

    def test_new_incident_dispatches_one_alert(self):
        with mock.patch('apps.ingest.detection.dispatch_incident_alert') as disp:
            for port in range(8000, 8008):
                _event(event_type=SecurityEvent.CONNECTION, dest_port=port)
        self.assertEqual(disp.call_count, 1)   # solo el incidente nuevo

    def test_dedup_does_not_renotify(self):
        with mock.patch('apps.ingest.detection.dispatch_incident_alert') as disp:
            for port in range(8000, 8016):     # cruza el umbral y sigue
                _event(event_type=SecurityEvent.CONNECTION, dest_port=port)
        self.assertEqual(disp.call_count, 1)   # no re-notifica el mismo (regla, IP)
```
(Necesita `from .detection import evaluate, get_sensor_user` en el import existente.)

- [ ] **Step 4: Run tests, verify they FAIL**

Run: `docker compose exec backend python manage.py test apps.ingest.tests.NotificationTests -v 2`
Expected: FAIL (`dispatch_incident_alert` no existe aún en detection).

- [ ] **Step 5: Enganchar en `detection.py`**

En el import de detection.py añadir: `from .notifications import dispatch_incident_alert`.
Dentro de `_fire`, en el bloque `if created:` (justo después de `generate_action_plan(incident)`):
```python
        generate_action_plan(incident)  # RF6: mismo plan automático que la V1
        dispatch_incident_alert(incident)  # Playbook SOAR: notifica al equipo (email, async)
```

- [ ] **Step 6: Run tests, verify PASS**

Run: `docker compose exec backend python manage.py test apps.ingest.tests.NotificationTests -v 2`
Expected: PASS (3 tests).

- [ ] **Step 7: Commit**

```bash
git add backend/apps/ingest/notifications.py backend/apps/ingest/detection.py backend/apps/ingest/tests.py backend/sgis/settings/base.py
git commit -m "feat(soar): notificación por email al crear incidente automático (playbook)"
```

---

## Task 2: Campo `alerted_at` (señal del paso Notificar en el tablero)

**Files:**
- Modify: `backend/apps/ingest/models.py` (`BlockedIP`)
- Modify: `backend/apps/ingest/detection.py` (`_fire`)
- Create: `backend/apps/ingest/migrations/0003_blockedip_alerted_at.py` (generada)
- Modify: `backend/apps/ingest/serializers.py` (`BlockedIPSerializer`)

- [ ] **Step 1: Añadir el campo al modelo**

En `BlockedIP` (models.py), tras `released_at`:
```python
    alerted_at = models.DateTimeField(null=True, blank=True, verbose_name='Notificado el')
```

- [ ] **Step 2: Setear `alerted_at` en `_fire`**

`_contain` ya devuelve la IP. Para registrar la notificación, en `_fire`, dentro de `if created:` tras `dispatch_incident_alert(incident)`:
```python
        dispatch_incident_alert(incident)
        BlockedIP.objects.filter(source_ip=event.source_ip).update(alerted_at=timezone.now())
```
(El `BlockedIP` ya fue creado por `_contain`, que se llama antes en `_fire`. Importar `timezone` ya está en detection.py.)

- [ ] **Step 3: Exponer en el serializer**

En `serializers.py`, `BlockedIPSerializer.Meta.fields` → asegurarse de incluir:
`['id', 'source_ip', 'rule', 'reason', 'incident', 'created_at', 'alerted_at']`.

- [ ] **Step 4: Generar y aplicar la migración**

Run:
```bash
docker compose exec backend python manage.py makemigrations ingest
docker compose exec backend python manage.py migrate
```
Expected: crea `0003_blockedip_alerted_at`, aplica OK.

- [ ] **Step 5: Test que `alerted_at` queda seteado**

Añadir a `NotificationTests`:
```python
    def test_containment_records_alerted_at(self):
        for port in range(8000, 8008):
            _event(event_type=SecurityEvent.CONNECTION, dest_port=port)
        b = BlockedIP.objects.get(source_ip='10.0.0.5')
        self.assertIsNotNone(b.alerted_at)
```
Run: `docker compose exec backend python manage.py test apps.ingest.tests.NotificationTests.test_containment_records_alerted_at -v 2` → PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/apps/ingest/models.py backend/apps/ingest/detection.py backend/apps/ingest/serializers.py backend/apps/ingest/migrations/0003_blockedip_alerted_at.py backend/apps/ingest/tests.py
git commit -m "feat(soar): BlockedIP.alerted_at para reflejar el paso Notificar en el tablero"
```

---

## Task 3: Liberar contención (paso "Revisar/Liberar")

**Files:**
- Modify: `backend/apps/ingest/views.py` (`ReleaseBlockView`)
- Modify: `backend/apps/ingest/urls.py`
- Test: `backend/apps/ingest/tests.py`

- [ ] **Step 1: Write the failing test**

```python
from apps.accounts.models import CustomUser
from rest_framework.test import APIClient

class ReleaseTests(TestCase):
    def _block(self):
        for port in range(8000, 8008):
            _event(event_type=SecurityEvent.CONNECTION, dest_port=port)
        return BlockedIP.objects.get(source_ip='10.0.0.5')

    def _client(self, role):
        u = CustomUser.objects.create_user(username=f'u_{role}', password='x', role=role)
        c = APIClient(); c.force_authenticate(u); return c

    def test_release_deactivates_and_drops_from_blocklist(self):
        self._block()
        c = self._client(CustomUser.ANALISTA)
        r = c.post('/api/ingest/blocklist/10.0.0.5/release/')
        self.assertEqual(r.status_code, 200)
        self.assertFalse(BlockedIP.objects.get(source_ip='10.0.0.5').active)

    def test_jefe_area_cannot_release(self):
        self._block()
        c = self._client(CustomUser.JEFE_AREA)
        r = c.post('/api/ingest/blocklist/10.0.0.5/release/')
        self.assertEqual(r.status_code, 403)
```
(Verificar los nombres reales de roles en `apps/accounts/models.py`: `ADMIN_TI`, `ANALISTA`, `JEFE_AREA`. Ajustar si difieren.)

- [ ] **Step 2: Run test, verify FAIL** (404, ruta no existe).
Run: `docker compose exec backend python manage.py test apps.ingest.tests.ReleaseTests -v 2`

- [ ] **Step 3: `ReleaseBlockView` en views.py**

```python
from apps.incidents.models import IncidentStatusHistory


class CanManageContainment(BasePermission):
    """Solo analista o admin_ti revisan/liberan contenciones."""
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role in ('analista', 'admin_ti'))


class ReleaseBlockView(APIView):
    """POST /api/ingest/blocklist/<ip>/release/ — levanta la contención (human-in-the-loop)."""
    permission_classes = [IsAuthenticated, CanManageContainment]

    def post(self, request, source_ip):
        try:
            block = BlockedIP.objects.get(source_ip=source_ip, active=True)
        except BlockedIP.DoesNotExist:
            return Response({'detail': 'IP no está en contención activa.'}, status=status.HTTP_404_NOT_FOUND)
        block.active = False
        block.released_at = timezone.now()
        block.save(update_fields=['active', 'released_at'])
        if block.incident_id:
            IncidentStatusHistory.objects.create(
                incident=block.incident, previous_status=block.incident.status,
                new_status=block.incident.status, changed_by=request.user,
                comment=f"Contención levantada manualmente sobre {source_ip}.",
            )
        return Response({'released': source_ip})
```

- [ ] **Step 4: Ruta en urls.py**

```python
from .views import (EventIngestView, OperationsFeedView, BlocklistView,
                    ReleaseBlockView)
# ...
    path('blocklist/<str:source_ip>/release/', ReleaseBlockView.as_view(), name='ingest-release'),
```

- [ ] **Step 5: Run tests, verify PASS.** (2 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/apps/ingest/views.py backend/apps/ingest/urls.py backend/apps/ingest/tests.py
git commit -m "feat(soar): endpoint para liberar contención (analista/admin_ti)"
```

---

## Task 4: Reiniciar demo (helper + comando + endpoint)

**Files:**
- Create: `backend/apps/ingest/maintenance.py`
- Create: `backend/apps/ingest/management/commands/reset_demo.py`
- Modify: `backend/apps/ingest/views.py`, `urls.py`
- Test: `backend/apps/ingest/tests.py`

- [ ] **Step 1: `maintenance.py`**

```python
"""Reinicio de la demo: borra SOLO lo generado por el sensor, deja intacto lo demás."""
from apps.incidents.models import Incident
from .models import SecurityEvent, BlockedIP


def reset_demo_data():
    """Borra eventos, bloqueos e incidentes automáticos del sensor. Devuelve conteos."""
    auto = Incident.objects.filter(created_by__username='sensor')
    counts = {
        'incidents': auto.count(),
        'events': SecurityEvent.objects.count(),
        'blocked': BlockedIP.objects.count(),
    }
    auto.delete()                 # cascada: historial, plan, blocked_ips, events FK
    SecurityEvent.objects.all().delete()
    BlockedIP.objects.all().delete()
    return counts
```

- [ ] **Step 2: Comando `reset_demo.py`**

`backend/apps/ingest/management/commands/reset_demo.py`:
```python
from django.core.management.base import BaseCommand
from apps.ingest.maintenance import reset_demo_data


class Command(BaseCommand):
    help = 'Borra eventos, bloqueos e incidentes automáticos del sensor (deja demo/manuales).'

    def handle(self, *args, **opts):
        c = reset_demo_data()
        self.stdout.write(self.style.SUCCESS(
            f"Reset: {c['incidents']} incidentes, {c['events']} eventos, {c['blocked']} bloqueos."))
```

- [ ] **Step 3: Failing test**

```python
class ResetTests(TestCase):
    def test_reset_clears_sensor_data_keeps_manual(self):
        manual = Incident.objects.create(
            title='Manual', description='x', incident_type=Incident.OTRO,
            criticality=Incident.BAJO, status=Incident.ABIERTO, affected_area='X',
            created_by=CustomUser.objects.create_user(username='ana', password='x', role='analista'),
        )
        for port in range(8000, 8008):
            _event(event_type=SecurityEvent.CONNECTION, dest_port=port)
        from .maintenance import reset_demo_data
        reset_demo_data()
        self.assertEqual(SecurityEvent.objects.count(), 0)
        self.assertEqual(BlockedIP.objects.count(), 0)
        self.assertFalse(Incident.objects.filter(created_by__username='sensor').exists())
        self.assertTrue(Incident.objects.filter(id=manual.id).exists())  # el manual sobrevive
```
Run → FAIL (no existe `maintenance`).

- [ ] **Step 4: `ResetDemoView` (solo admin_ti) + ruta**

views.py:
```python
from .maintenance import reset_demo_data

class IsAdminTI(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role == 'admin_ti')

class ResetDemoView(APIView):
    """POST /api/ingest/reset/ — limpia el tablero para repetir la demo (admin_ti)."""
    permission_classes = [IsAuthenticated, IsAdminTI]
    def post(self, request):
        return Response(reset_demo_data())
```
urls.py: `path('reset/', ResetDemoView.as_view(), name='ingest-reset'),` (+ import).

- [ ] **Step 5: Run tests, verify PASS.** Correr toda la suite: `docker compose exec backend python manage.py test apps.ingest -v 2` → todo verde.

- [ ] **Step 6: Commit**

```bash
git add backend/apps/ingest/maintenance.py backend/apps/ingest/management/commands/reset_demo.py backend/apps/ingest/views.py backend/apps/ingest/urls.py backend/apps/ingest/tests.py
git commit -m "feat(soar): reiniciar demo (comando reset_demo + endpoint admin_ti)"
```

---

## Task 5: Sensor — firewall real (`netsh`) + reconcile por diff

**Files:**
- Modify: `tools/sensor.py`
- Test: self-check con `assert` dentro de `sensor.py` (función pura), corrible con `python tools/sensor.py --selftest`.

- [ ] **Step 1: Función pura `diff_blocklist` + self-test**

Añadir a sensor.py:
```python
def diff_blocklist(desired: set, current: set):
    """Reconcile declarativo: qué IPs bloquear de nuevo y cuáles liberar."""
    return desired - current, current - desired   # (to_add, to_remove)


def _selftest():
    assert diff_blocklist({'a', 'b'}, set()) == ({'a', 'b'}, set())
    assert diff_blocklist({'a'}, {'a', 'b'}) == (set(), {'b'})
    assert diff_blocklist({'a'}, {'a'}) == (set(), set())
    print("selftest OK")
```
En `main()`, añadir `--selftest` que llame a `_selftest()` y salga.

- [ ] **Step 2: Helpers `netsh` (Windows, best-effort)**

```python
import subprocess

def _is_windows_admin():
    if os.name != 'nt':
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False

def _fw_add(ip):
    subprocess.run(['netsh', 'advfirewall', 'firewall', 'add', 'rule',
                    f'name=SGIS-block-{ip}', 'dir=in', 'action=block', f'remoteip={ip}'],
                   capture_output=True)

def _fw_del(ip):
    subprocess.run(['netsh', 'advfirewall', 'firewall', 'delete', 'rule',
                    f'name=SGIS-block-{ip}'], capture_output=True)
```

- [ ] **Step 3: Integrar el reconcile en `run_listen`**

- `run_listen` recibe `use_firewall: bool`.
- Calcular `fw_on = use_firewall and _is_windows_admin()`; si `use_firewall and not fw_on`: `log("firewall real no disponible (sin admin/no-Windows) → corto solo en la app", 'yel')`.
- Mantener `blocked` como `set`. En cada refresco:
```python
        desired = fetch_blocklist(base_url, api_key)
        to_add, to_remove = diff_blocklist(desired, blocked)
        if fw_on:
            for ip in to_add: _fw_add(ip)
            for ip in to_remove: _fw_del(ip)
        for ip in to_add: log(f"{ip:>15} ⛔ contención aplicada", 'red')
        for ip in to_remove: log(f"{ip:>15} ✔ contención levantada", 'yel')
        blocked = desired
```
- En `finally` (al salir): `if fw_on:` borrar todas las reglas de las IPs aún en `blocked` (`for ip in blocked: _fw_del(ip)`).

- [ ] **Step 4: Flag `--firewall` en `main()` y pasarlo**

```python
    p.add_argument('--firewall', action='store_true',
                   help='Aplica reglas de Windows Firewall reales (requiere admin)')
    # ...
        run_listen(endpoint, args.target, args.api_key, args.name, ports, args.auth_port, args.bind, args.firewall)
```
(Actualizar la firma de `run_listen`.)

- [ ] **Step 5: Verificar**

Run: `python tools/sensor.py --selftest` → "selftest OK".
Run (Linux dev, sin firewall): `python tools/sensor.py --target http://localhost:8001` arranca y, al pedir `--firewall`, avisa el fallback. (Smoke manual; netsh real se prueba en W11 el día del ensayo.)

- [ ] **Step 6: Commit**

```bash
git add tools/sensor.py
git commit -m "feat(soar): sensor aplica firewall real (netsh) con reconcile por diff y fallback a corte app"
```

---

## Task 6: Frontend — playbook por IP + botones Liberar/Reiniciar

**Files:**
- Modify: `frontend/src/stores/incidents.js`
- Modify: `frontend/src/views/OperationsView.vue`

- [ ] **Step 1: Métodos del store**

En `stores/incidents.js` (siguiendo el patrón de las acciones existentes con `axios`):
```js
async releaseBlock(ip) { await axios.post(`/ingest/blocklist/${ip}/release/`) },
async resetDemo() { await axios.post('/ingest/reset/') },
```

- [ ] **Step 2: Playbook por IP en el panel SOAR**

En `OperationsView.vue`, dentro del `v-for` de `blockedIps`, bajo cada IP, una fila de pasos. Usar un helper:
```html
<div class="pb-steps">
  <span class="pb on">Detectar</span>
  <span class="pb on">Contener</span>
  <span class="pb" :class="{ on: b.alerted_at }">Notificar</span>
  <span class="pb on">Documentar</span>
  <button class="pb-release" @click="liberar(b.source_ip)">Liberar</button>
</div>
```
Script:
```js
async function liberar(ip) {
  await store.releaseBlock(ip)
  blockedIps.value = blockedIps.value.filter(b => b.source_ip !== ip)  // optimista
  poll()
}
```
CSS mínimo (estética actual): `.pb` gris, `.pb.on` negro/✓, `.pb-release` botón pequeño rojo.

- [ ] **Step 3: Botón "Reiniciar demo" (solo admin_ti)**

En `.page-head .head-actions`, antes del live-badge:
```html
<button v-if="isAdminTI" class="reset-btn" @click="reiniciar">Reiniciar demo</button>
```
Script: leer el rol desde el `auth` store; `async function reiniciar(){ if(confirm('¿Borrar eventos, bloqueos e incidentes automáticos?')){ await store.resetDemo(); poll() } }`.

- [ ] **Step 4: Verificar en el navegador**

Levantar frontend (`docker compose up frontend` o el dev server), loguear como `admin.ti`, disparar el sensor/replay, ver pasos del playbook + Liberar (la IP desaparece) + Reiniciar (tablero a cero). Smoke manual.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/stores/incidents.js frontend/src/views/OperationsView.vue
git commit -m "feat(soar): tablero muestra el playbook por IP + botones Liberar y Reiniciar demo"
```

---

## Task 7: Kit de demo — Launcher PowerShell

**Files:**
- Create: `tools/Launcher.ps1`, `tools/Iniciar.bat`, `tools/LEEME.txt`
- Verificar: `INGEST_API_KEY` real en Railway (MCP railway `list_variables` o dashboard) → default del launcher.

- [ ] **Step 1: Verificar la API key de Railway** y anotarla como default en el launcher (campo editable igual).

- [ ] **Step 2: `Iniciar.bat`**

```bat
@echo off
powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0Launcher.ps1"
```

- [ ] **Step 3: `Launcher.ps1` — GUI WinForms rol-aware** (implementar según spec §6):
  - `Add-Type -AssemblyName System.Windows.Forms, System.Drawing`.
  - Ventana con: ComboBox de rol (Atacante/Sensor/Operador), campos de config (URL Railway, API Key, [IP sensor]), panel de botones que cambia con el rol, y un `RichTextBox` de log.
  - Sensor: muestra IP LAN (`Get-NetIPAddress`/`Test-Connection`), botón "Iniciar sensor (firewall real)" → `Start-Process powershell -Verb RunAs -ArgumentList "python sensor.py --target <url> --firewall"`, "Iniciar (solo app)" sin `-Verb RunAs`, "Detener".
  - Atacante: botones que invocan `attacker.ps1 -Target <ipSensor>` (escaneo/fuerza/completo).
  - Operador: "Abrir Centro de Operaciones" → `Start-Process https://sgis-ucv.vercel.app`, "Mostrar credenciales".
  - Cada acción escribe en el log.

- [ ] **Step 4: `LEEME.txt`**

```
KIT DE DEMO SGIS-UCV
1. Copia esta carpeta (tools/) completa a la laptop.
2. Doble clic en Iniciar.bat.
3. Elige el rol de esta laptop (Atacante / Sensor / Operador).
4. SENSOR: anota la "IP LAN" que muestra → es la que teclea el atacante.
5. ATACANTE: escribe esa IP y pulsa "Ataque completo".
(Sensor necesita Python instalado; el resto no instala nada.)
```

- [ ] **Step 5: Verificar** (en W11 si hay; si no, revisión de sintaxis PowerShell + ensayo el día). Smoke manual.

- [ ] **Step 6: Commit**

```bash
git add tools/Launcher.ps1 tools/Iniciar.bat tools/LEEME.txt
git commit -m "feat(demo): launcher PowerShell rol-aware (kit de despliegue por laptop)"
```

---

## Task 8: Runbook de la demo

**Files:**
- Modify: `tools/README.md`

- [ ] **Step 1:** Añadir sección "Demo de campo (Fase 3)": los 7 beats, el reparto roles↔laptops, el checklist de Leo (internet, Python, admin, SMTP en Railway) y el plan B (`--replay`).
- [ ] **Step 2: Commit** `docs: runbook de la demo de campo (7 beats + reparto + checklist)`.

---

## Self-Review (cobertura del spec)

- §3.1 Notificar email → Task 1 ✓ · §3.2 `alerted_at` → Task 2 ✓ · §3.3 Liberar → Task 3 ✓ · §3.4 Reiniciar → Task 4 ✓ · §3.5 Feed (`alerted_at` en serializer) → Task 2 step 3 ✓
- §4 Sensor firewall → Task 5 ✓ · §5 Frontend → Task 6 ✓ · §6 Kit/launcher → Task 7 ✓ · §7 verificar API key → Task 7 step 1 ✓ · §8 pruebas → Tasks 1-5 (tests/selftest) ✓ · runbook §10.6 → Task 8 ✓
- **Nota de verificación de roles:** confirmar en `apps/accounts/models.py` los valores exactos del campo `role` (`admin_ti`/`analista`/`jefe_area`) y los nombres de constantes (`ADMIN_TI`...) antes de los tests de permisos (Tasks 3-4).
