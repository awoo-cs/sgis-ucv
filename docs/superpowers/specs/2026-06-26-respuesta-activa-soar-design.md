# SGIS-UCV V1.1 — Respuesta Activa (salto SIEM → SOAR)

- **Fecha:** 2026-06-26
- **Estado:** Diseño aprobado (pendiente de review del spec → plan de implementación)
- **Motiva:** 2da revisión con el docente. Veredicto: el proyecto más interesante y escalable de la clase. Único "pero": *"los incidentes ahora se crean solos, pero **¿qué acciones toma el sistema** cuando los detecta?"*. Un compañero añadió que al ser web es *"fácil de vulnerar"* y *"muy pasivo"*.
- **Objetivo en una frase:** que el sistema pase de **solo detectar** a **detectar y actuar** — contención automática del atacante, demostrable en vivo.

---

## 1. El concepto: la R que falta

Hoy el mini-SIEM hace la **D** de SOAR (*Detección*). Falta la **R** (*Respuesta*). Este es el salto **SIEM → SOAR** (*Security Orchestration, Automation & Response*): el sistema no solo ve y avisa, **decide y actúa**.

La acción estrella es la **contención automática**: al detectar un atacante, el sistema le **bloquea el acceso** sin que nadie toque nada. Sobre esa base se montan más tipos de respuesta, el control humano para revertirla, y el blindaje del propio login.

## 2. La estrella polar: la demo en vivo

Todo el diseño existe para que este guion funcione frente al docente (switch + cables + laptops). Lo que el docente valora es el **flujo**, no el código.

| Beat | Qué pasa en pantalla |
|------|----------------------|
| 0 | Dos laptops en el switch: **atacante** y **protegida** (corre el sensor). En el proyector, el **Centro de Operaciones** en vivo. |
| 1 | El atacante lanza escaneo / fuerza bruta. **Nadie toca el SGIS.** |
| 2 | En 2-3s aparece **solo** un incidente rojo. *"Nadie lo creó. El sistema lo vio."* |
| 3 | Acto seguido: **🛡️ CONTENIDO — IP bloqueada 10:02:04**. Detectado 10:02:03 → contenido 10:02:04. *"Un humano tarda minutos; el sistema, un segundo."* |
| 4 | *"¿No me creen?"* El atacante reintenta → **connection refused**. Está afuera, **de verdad**. |
| 5 | El incidente registra *"Contención automática ejecutada"* como evidencia (reúsa el plan de la Fase 2). |

El **beat 4** (bloqueo real y verificable) es lo que responde al docente y calla la crítica de "pasivo / vulnerable".

## 3. Arquitectura: el lazo cerrado

La orden de bloqueo **viaja de vuelta en la misma respuesta** del POST que reportó el ataque. El sensor ya habla con el servidor; el servidor solo le contesta *"y de paso, bloquea a este"*. **Cero canales nuevos.**

```
atacante ──TCP──► sensor ──POST /api/ingest/events/──► evaluate() ─► incidente
                    ▲                                       │           │
                    │                                  apply_responses()│
                    │   respuesta: { blocked_ips:[...] } ◄──────────────┘
              reconcile(desired):
                · IP nueva  → cierra la puerta (+ netsh best-effort)
                · IP retirada → abre la puerta
                    │
              CONTENIDO en el Centro de Operaciones + evidencia en el incidente
```

**Principio clave — blocklist declarativa, no órdenes sueltas.** El servidor no manda "bloquea" / "desbloquea" como eventos; publica **el estado deseado** (`blocked_ips`). El sensor *reconcilia*: bloquea las nuevas, desbloquea las que ya no están. Esto unifica bloqueo + desbloqueo en un solo mecanismo, es idempotente y se auto-cura tras un reinicio (el sensor re-sincroniza). *Ponytail: modelo declarativo = lo mínimo correcto para soportar bloquear y desbloquear sin lógica duplicada.*

Para que el desbloqueo llegue **aunque ya no fluyan eventos** (el atacante está bloqueado, no genera tráfico), el sensor además **consulta** la blocklist cada ~2s (`GET /api/ingest/blocklist/`). El bloqueo es instantáneo por la respuesta del POST; el poll mantiene el estado fresco y entrega los desbloqueos.

## 4. Modelo de datos

Una sola abstracción nueva soporta los tres pedidos (más tipos de respuesta, desbloqueo manual, blindaje del login). Vive en `apps/ingest` (misma tubería ingestar → detectar → responder). *Ponytail: no creo una app nueva hasta que esto crezca.*

```python
# apps/ingest/models.py
class ResponseAction(models.Model):
    BLOCK_IP        = 'block_ip'         # bloquear la IP atacante (sensor + web)
    DISABLE_ACCOUNT = 'disable_account'  # desactivar una cuenta comprometida
    ESCALATE        = 'escalate'         # subir criticidad / asignar a admin_ti
    NOTIFY          = 'notify'           # alerta destacada en el Centro de Operaciones
    ISOLATE_HOST    = 'isolate_host'     # (definido; hoy se comporta como block_ip)

    PENDING = 'pending'; APPLIED = 'applied'; FAILED = 'failed'; LIFTED = 'lifted'

    incident   = models.ForeignKey('incidents.Incident', related_name='response_actions', ...)
    action_type= models.CharField(choices=...)
    params     = models.JSONField(default=dict)   # p.ej. {"ip": "192.168.1.50"}
    status     = models.CharField(choices=..., default=PENDING)
    auto       = models.BooleanField(default=True) # True = lo creó el motor
    note       = models.CharField(...)             # regla / motivo
    created_at = models.DateTimeField(auto_now_add=True)
    applied_at = models.DateTimeField(null=True)
    lifted_at  = models.DateTimeField(null=True)
    lifted_by  = models.ForeignKey(User, null=True, ...)  # human-in-the-loop
```

**La blocklist es una consulta derivada**, no un estado paralelo:
```python
blocked_ips = ResponseAction.objects.filter(
    action_type=ResponseAction.BLOCK_IP, status=ResponseAction.APPLIED
).values_list('params__ip', flat=True)
```

## 5. El motor de respuesta

Espejo de `action_plans/plan_templates.py`: una tabla regla → respuestas, leíble de un vistazo.

```python
# apps/ingest/response_templates.py
RESPONSE_TEMPLATES = {
    'port_scan':         ['block_ip', 'notify'],
    'brute_force':       ['block_ip', 'notify'],
    'blacklist_ip':      ['block_ip', 'escalate'],
    'login_brute_force': ['block_ip', 'notify'],   # fuerza bruta contra el propio login
}
```

```python
# apps/ingest/response.py
def apply_responses(incident, rule, *, source_ip=None, target_user=None):
    """Crea y ejecuta las ResponseAction que la regla manda. Idempotente."""
    for action_type in RESPONSE_TEMPLATES.get(rule, ['notify']):
        action = ResponseAction.objects.create(incident=incident, action_type=action_type, ...)
        _HANDLERS[action_type](action, source_ip=source_ip, target_user=target_user)
```

**Handlers (cada uno mínimo):**
- `block_ip` → guarda `params={"ip": source_ip}`, marca `applied`. *La ejecución la hacen el sensor y el middleware web leyendo la blocklist; el handler solo declara la intención.*
- `disable_account` → si se conoce la cuenta, `user.is_active = False` (1 línea de Django). Si no, `failed`.
- `escalate` → `incident.criticality = CRITICO`, reasigna a un `admin_ti`. Reúsa campos de la Fase 2.
- `notify` → la propia `ResponseAction` es la notificación; el Centro de Operaciones la pinta como alerta destacada. *Ponytail: sin email/SMS — in-app basta.*
- `isolate_host` → hoy delega en `block_ip`. *Ponytail: definido para el catálogo, sin segundo mecanismo hasta que se pida.*

**Enganche:** en `detection.py::_fire`, justo después de `generate_action_plan(incident)` y **solo cuando el incidente es nuevo** (`created`), se llama `apply_responses(...)`. En incidentes reusados (anti-dup) el bloqueo ya existe y persiste.

## 6. Ejecución del bloqueo (las dos superficies)

La misma blocklist se hace cumplir en dos lugares:

**(a) Red — el sensor** (`tools/sensor.py`, stdlib):
- Mantiene un `set` local. Tras cada respuesta de POST y en cada poll, `reconcile(desired)`:
  - IP nueva → la mete en su deny-set (el listener **cierra la conexión de entrada** de esa IP → el atacante ve *connection refused*) **+** intento *best-effort* de `netsh advfirewall firewall add rule ... action=block remoteip=<ip>`.
  - IP retirada → la saca del deny-set **+** `netsh ... delete rule`.
- *Ponytail: blocklist en memoria, el servidor es la fuente de verdad; se pierde al reiniciar y se re-sincroniza solo.*

**(b) Web — middleware Django** (`BlocklistMiddleware`):
- En cada request, si la IP del cliente está en la blocklist → **403**. Así el propio SGIS bloquea a los atacantes (responde directo al *"web fácil de vulnerar"*).
- *Ponytail: blocklist cacheada ~5s para no pegarle a la BD por cada request.*

**El detalle Windows:** `netsh` necesita admin y puede no estar disponible en una laptop prestada. **La demo no depende de eso**: el cierre de puerta a nivel del sensor funciona siempre, sin admin, multiplataforma. El `netsh` es un *bonus* que añade el bloqueo a nivel de todo el sistema cuando hay permisos; si falla, se ignora en silencio.

## 7. Desbloqueo manual (human-in-the-loop)

El analista/admin puede **levantar la contención** (falso positivo o amenaza ya gestionada):

- `POST /api/ingest/response-actions/{id}/lift/` (JWT, `analista` o `admin_ti`) → `status=lifted`, `lifted_by`, `lifted_at`.
- Al salir de la consulta derivada, la IP desaparece de `blocked_ips` → en el siguiente `reconcile` (≤2s) el sensor **abre la puerta** y el middleware deja pasar.
- **Auto-levantado:** al cerrar el incidente (`→ cerrado`), sus `block_ip` activos pasan a `lifted` (la amenaza ya se gestionó). Reúsa el ciclo de vida existente.
- En el Centro de Operaciones, cada IP contenida muestra estado **ACTIVO → CONTENIDO** y un botón **"Levantar contención"**.

## 8. Blindaje del login (y dogfooding al SIEM)

Responde al *"web fácil de vulnerar"* en capas, sin dependencias nuevas:

1. **Throttle nativo de DRF** sobre el endpoint de login: `ScopedRateThrottle` con scope `login` a `5/min` por IP → al 6º intento, **429**. (DRF ya está instalado; son pocas líneas en `settings` + la vista.)
2. **Dogfooding — el login alimenta su propio SIEM:** ante un login fallido, se emite **en proceso** un `SecurityEvent(event_type=AUTH_FAILURE, source_ip=<cliente>, username=<intentado>, sensor='SGIS-Login')` y se llama a `evaluate()`. La **regla `brute_force` existente** (≥5 fallos/60s) dispara el incidente + la contención. La IP entra a la blocklist → el **middleware web** la corta. *El propio login resiste el mismo ataque que el sistema detecta.*
   - El throttle (paso 1) y el umbral de la regla (5/60s) evitan que un par de tipos de un usuario legítimo dispare nada.

*Ponytail: el bloqueo por IP (throttle + blocklist) es el 80%. El lockout por usuario queda cubierto por `disable_account` cuando la cuenta objetivo es conocida; no añado un sistema de lockout aparte.*

## 9. Cambios en la API

| Método | Endpoint | Cambio |
|--------|----------|--------|
| `POST` | `/api/ingest/events/` | La respuesta **incluye** `blocked_ips: [...]` (bloqueo instantáneo). |
| `GET` | `/api/ingest/blocklist/` | **Nuevo.** Auth `X-API-Key`. Devuelve `{"blocked_ips": [...]}` para que el sensor reconcilie. |
| `POST` | `/api/ingest/response-actions/{id}/lift/` | **Nuevo.** JWT (`analista`/`admin_ti`). Levanta la contención. |
| `GET` | `/api/incidents/{id}/` | Añade `response_actions` anidadas (igual que `action_plan`). |
| `GET` | `/api/ingest/feed/` | Añade las response actions recientes para el Centro de Operaciones. |

## 10. Frontend (Centro de Operaciones)

- **Momento CONTENIDO:** cuando una contención se aplica, banner **🛡️ CONTENIDO** con la IP y el **tiempo de reacción** (`detectado → contenido`, p.ej. *1s*).
- **Estado por IP:** ACTIVO (rojo) → CONTENIDO (negro).
- **Botón "Levantar contención"** por IP/acción (visible a `analista`/`admin_ti`).
- **Detalle del incidente:** lista de `response_actions` con tipo, hora y quién la levantó (si aplica) — como evidencia, junto al plan de la Fase 2.

## 11. Pruebas

Reúsa el estilo de `apps/ingest/tests.py`:
- El motor crea las `ResponseAction` correctas por regla (mapeo de plantilla).
- `block_ip` aparece en `/blocklist/`; tras `lift/` desaparece.
- `disable_account` deja `user.is_active = False`.
- Login: 6º intento/min → 429; tras 5 fallos → `SecurityEvent` + incidente + IP en la blocklist; el middleware responde 403 a esa IP.
- `reconcile(desired)` (función pura del sensor): IP nueva cierra, IP retirada abre. **Self-check mínimo** con `assert` (sin frameworks).

## 12. Runbook de demo y red de seguridad

- Extender `tools/README.md` con los 6 beats y el setup de 2 laptops.
- **Red de seguridad** (por si la red del salón falla, como en el 1er avance): `python tools/sensor.py --replay` reproduce **detección + contención + evidencia** en pantalla (beats 2-3-5) sin atacante real. El **beat 4** (refused en vivo) requiere las 2 laptops reales. Ampliar `events_replay.json` para que el replay dispare una contención.

## 13. Fuera de alcance (YAGNI)

- Notificaciones por email/SMS (solo in-app).
- Persistir la blocklist del sensor entre reinicios (re-sincroniza del servidor).
- Programar el switch físico (se bloquea en host/app, no en el switch).
- Framework de agentes distribuidos (el sensor **es** el agente).
- `isolate_host` como mecanismo propio (hoy = `block_ip`).

## 14. Plan por fases

1. **Motor de respuesta (backend):** `ResponseAction` + `response_templates` + `apply_responses` enganchado en `detection.py`. Handlers `block_ip`/`escalate`/`notify`/`disable_account`. Endpoint `/blocklist/` + `blocked_ips` en la respuesta de eventos. Tests.
2. **Músculo (sensor):** `reconcile(desired)` + cierre de puerta + `netsh` best-effort + poll cada ~2s. Self-check.
3. **Blindaje del login:** throttle DRF + dogfooding al SIEM + `BlocklistMiddleware` (403). Tests.
4. **Espejo (frontend):** momento CONTENIDO + tiempo de reacción + `response_actions` en el detalle + botón "Levantar contención".
5. **Ensayo:** runbook de los 6 beats + `events_replay.json` con contención + notas de la red de seguridad.
