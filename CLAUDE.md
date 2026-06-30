# SGIS-UCV — Sistema de Gestión de Incidentes de Seguridad

Plataforma web para el Centro de Cómputo de la Universidad César Vallejo (UCV). Registra, clasifica, asigna, da seguimiento y cierra incidentes de ciberseguridad, con planes de acción automáticos y exportación de reportes PDF.

**Curso:** Redes y Seguridad Perimetral — 2026  
**Docente:** Mgtr. Soldi Escobar, Emilio Cesar Nicolas  
**Equipo:** Castillo Valverde J., Chuquitapa Pérez S., Lazarte Moreno R., Liñan Huanca J., Pizarro Bordoy L.

---

## Estado y roadmap

- **2026-06-17** — Presentada la V1 (demo) al docente. Veredicto: idea buena pero proyecto **muy simple** → hacer una **V1.1 "remasterizada"**.
- **2026-06-26** — 2da revisión: el profe pidió pasar de **SIEM a SOAR** ("¿qué hace el sistema *después* de detectar?"). → **V1.2: respuesta activa** = al detectar, el sistema **contiene** automáticamente bloqueando la IP atacante (el sensor le corta la conexión en vivo). Pensado para demo sobre la LAN/switch del salón.
- **2026-06-29** — Fase 3 (SOAR V1.2) verificada y cerrada. Añadido el paso **Notificar** del playbook: al contener, se envía un **email de alerta** (ver "Notificación por email" abajo). Probado end-to-end en la nube **dev** (detectar → contener → notificar → email recibido). Kit demo (`tools/`) auditado y apuntando a dev, con apertura/cierre automático del firewall del sensor. main/producción **intactos**.
- **Próximas features a planear** (aún sin diseñar): generación automática de reportes de incidentes a partir de eventos de un **firewall**, y **planes de acción automáticos** más completos.
- Informe de justificación técnica entregado al docente: `../Informe_Justificacion_Tecnica_SGIS-UCV.docx`.

---

## URLs de producción

| Servicio | URL |
|----------|-----|
| **Frontend (Vercel)** | https://sgis-ucv.vercel.app |
| **Backend API (Railway)** | https://backend-production-7cfc1.up.railway.app |
| **Django Admin (Railway)** | https://backend-production-7cfc1.up.railway.app/admin |
| **GitHub** | https://github.com/awoo-cs/sgis-ucv |

---

## Stack

| Capa | Tecnología | Hospedaje |
|------|-----------|-----------|
| Frontend | Vue.js 3 + Vuetify 3 + Pinia + Vue Router 4 + Axios | Vercel |
| Backend | Django 4.2 + DRF 3.15 + SimpleJWT + gunicorn | Railway |
| Base de datos | PostgreSQL 16 | Railway (internal) |
| Contenedores (dev) | Docker + Docker Compose | local |
| Reportes | ReportLab (PDF) | — |

---

## Desarrollo local

```bash
cd sgis-ucv
cp .env.example .env          # solo la primera vez
docker compose up --build     # levanta db + backend + frontend
```

El backend corre `makemigrations` + `migrate` + `loaddata` + `create_demo_data` automáticamente.

| Servicio | URL local |
|----------|-----------|
| Frontend (Vue) | http://localhost:5173 |
| Backend (API) | http://localhost:8000 |
| Django Admin | http://localhost:8000/admin |

**Reinicio limpio** (borra la base de datos):
```bash
docker compose down -v && docker compose up --build
```

**Cargar datos de demo manualmente:**
```bash
docker compose exec backend python manage.py create_demo_data
docker compose exec backend python manage.py create_demo_data --clear  # borra primero
```

---

## Usuarios de prueba (cargados automáticamente)

| Usuario | Contraseña | Rol |
|---------|-----------|-----|
| `admin.ti` | `Sgis2026*` | Administrador TI — acceso total + Django admin |
| `analista` | `Sgis2026*` | Analista de Seguridad — crear/gestionar incidentes |
| `jefe.area` | `Sgis2026*` | Jefe de Área — solo lectura y dashboard |

Seed: `backend/initial_data.json` vía `loaddata`. Datos demo: `create_demo_data.py` (45 incidentes ficticios).

---

## Git — flujo de ramas

```
dev  ──── trabajo diario, features, fixes ────► PR ──► main
 │                                                       │
 └─► Vercel preview automático                Vercel producción automático
     (URL única por commit)                   (sgis-ucv.vercel.app)
```

- **`dev`** → rama de trabajo. Todo commit genera un preview en Vercel automáticamente.
- **`main`** → producción. Merge **solo cuando el profesor lo indique explícitamente**.
- La integración GitHub-Vercel está activa: no se necesita el CLI para deploys normales.

```bash
git checkout dev               # siempre trabajar aquí
git push origin dev            # → genera preview en Vercel automáticamente
# Para producción: merge dev → main (pedir permiso primero)
```

---

## Deployment

### Vercel (frontend)

- **Proyecto:** `awoo-cs-projects/sgis-ucv` (ID: `prj_CN2nuq9XWHl52z1x3FgRYlHbo7xS`)
- **Dashboard:** https://vercel.com/awoo-cs-projects/sgis-ucv
- **GitHub conectado:** `awoo-cs/sgis-ucv` — rama `main` → producción, resto → preview
- **Root directory:** `frontend/`
- **Build:** `npm run build`, output `dist/`
- **Rewrites:** `/(.*) → /index.html` en `vercel.json` (SPA routing — sin esto, F5 da 404)
- **`VITE_API_BASE_URL`** configurada para `Production` **y** `Preview` → apunta al backend Railway

> **Crítico — VITE_ vars se bakean en build time:** Vite incrusta `import.meta.env.VITE_*` en el JS al compilar. Si se cambia el valor en el dashboard de Vercel, hay que forzar un redeploy (push vacío o desde el dashboard). No es suficiente con cambiar la variable.

Redeploy manual de emergencia (si el auto-deploy falla):
```bash
cd frontend/
VERCEL_TOKEN=<token> npx vercel --prod --token <token> --yes --scope awoo-cs-projects
```

Añadir/actualizar una env var via API (sin CLI):
```bash
# Crear
curl -X POST "https://api.vercel.com/v10/projects/prj_CN2nuq9XWHl52z1x3FgRYlHbo7xS/env?teamId=team_VkCUhWzVttjtzJlH5qUVPFKb" \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"key":"VITE_API_BASE_URL","value":"<url>","type":"plain","target":["production","preview"]}'
```

### Railway (backend + DB)

- **Proyecto:** `sgis-ucv` (ID: `a0ad21bb-4847-438f-9202-24bec06afac9`)
- **Dashboard:** https://railway.com/project/a0ad21bb-4847-438f-9202-24bec06afac9
- **Servicio backend:** `fc771fa3-5013-47f2-9afa-f825da32f903`
- **Servicio Postgres:** `b609d8d4-699f-438a-ac2a-5f6f76653f27`
- **Build:** Dockerfile en `backend/` (Python 3.12-slim + libpq-dev)
- **Start:** CMD en Dockerfile → `migrate --noinput` → `loaddata` → `create_demo_data` → `gunicorn`
- **Settings:** `sgis.settings.production` (CORS permite `*.vercel.app`)
- **DB interna:** `postgres.railway.internal:5432` (solo accesible dentro de Railway)

Redeploy manual del backend:
```bash
export PATH="$HOME/.railway/bin:$PATH"
railway login   # si no está autenticado
cd sgis-ucv
railway up ./backend --path-as-root --service backend --detach -m "descripción"
```

### Variables de entorno en Railway (backend)

| Variable | Valor |
|----------|-------|
| `DJANGO_SETTINGS_MODULE` | `sgis.settings.production` |
| `SECRET_KEY` | (generada, en Railway) |
| `DEBUG` | `False` |
| `POSTGRES_HOST` | `postgres.railway.internal` |
| `POSTGRES_DB` | `railway` |
| `POSTGRES_USER` | `postgres` |
| `POSTGRES_PORT` | `5432` |
| `ALLOWED_HOSTS` | `*` |
| `INGEST_API_KEY` | clave del sensor (cabecera `X-API-Key`) |
| `EMAIL_BACKEND` | `apps.ingest.resend_email.ResendEmailBackend` (HTTP, no SMTP) |
| `RESEND_API_KEY` | key de resend.com (envío de email por HTTP) |
| `DEFAULT_FROM_EMAIL` | `SGIS-UCV <onboarding@resend.dev>` (sin dominio propio) |
| `SOAR_ALERT_EMAIL` | destinatario de las alertas (default `leopb77@gmail.com`) |
| `SOAR_ALERT_WINDOW_SECONDS` | ventana del digest anti-saturación (default `300`) |

---

## Estructura de archivos

```
sgis-ucv/
├── docker-compose.yml
├── .env / .env.example
├── CLAUDE.md
│
├── backend/
│   ├── Dockerfile                           ← Usado por Railway en prod (Python 3.12-slim)
│   ├── Procfile                             ← Fallback si Railway no detecta Dockerfile
│   ├── requirements.txt                     ← Incluye gunicorn para producción
│   ├── manage.py                            ← DJANGO_SETTINGS_MODULE = production
│   ├── initial_data.json                    ← Fixture con 3 usuarios seed
│   ├── sgis/
│   │   ├── settings/
│   │   │   ├── base.py                      ← Config principal (DB, JWT, DRF, CORS)
│   │   │   ├── development.py               ← DEBUG=True, CORS_ALLOW_ALL_ORIGINS=True
│   │   │   └── production.py                ← DEBUG=False, CORS para *.vercel.app
│   │   ├── urls.py
│   │   └── wsgi.py
│   └── apps/
│       ├── accounts/                        ← CustomUser + JWT + permisos por rol
│       │   ├── models.py                    ← CustomUser (AbstractUser + role)
│       │   ├── serializers.py               ← CustomTokenObtainPairSerializer
│       │   ├── views.py
│       │   ├── urls.py
│       │   └── permissions.py               ← IsAdminTI, IsAdminTIOrAnalista, IsJefeArea
│       ├── incidents/                       ← Núcleo del sistema
│       │   ├── models.py                    ← Incident, IncidentStatusHistory, IncidentComment
│       │   ├── serializers.py               ← List / Detail / Create / Update
│       │   ├── views.py                     ← CRUD + dashboard_metrics
│       │   ├── filters.py                   ← IncidentFilter (django-filter)
│       │   ├── urls.py
│       │   └── management/commands/
│       │       └── create_demo_data.py      ← 45 incidentes ficticios con historial
│       ├── action_plans/                    ← Planes de acción automáticos (RF6)
│       │   ├── models.py                    ← ActionPlan (OneToOne → Incident)
│       │   ├── plan_templates.py            ← Plantillas por tipo × criticidad
│       │   ├── serializers.py
│       │   ├── views.py
│       │   └── urls.py
│       ├── reports/                         ← Exportación PDF (RF9)
│       │   ├── pdf_generator.py             ← ReportLab: tabla coloreada por criticidad
│       │   ├── views.py
│       │   └── urls.py
│       └── ingest/                          ← Mini-SIEM V1.1 + SOAR V1.2
│           ├── models.py                    ← SecurityEvent, BlockedIP, AlertThrottle
│           ├── detection.py                 ← Motor: 3 reglas → incidente + contención
│           ├── notifications.py             ← Email de alerta + digest anti-saturación (Opción A)
│           ├── resend_email.py              ← Backend de email por HTTP (Resend) — Railway bloquea SMTP
│           ├── ipv4_email.py                ← Backend SMTP forzando IPv4 (referencia; no usar en Railway)
│           ├── maintenance.py               ← reset_demo_data (limpia eventos/incidentes/contención/throttle)
│           ├── serializers.py
│           ├── views.py                     ← POST events (API-key) + GET feed (JWT) + reset (admin_ti)
│           ├── urls.py
│           └── tests.py                     ← 21 tests: detección, contención, throttle, email, reset
│
├── tools/                                   ← Kit de demo (solo stdlib, sin pip)
│   ├── sensor.py                            ← Honeypot: escucha puertos y reporta (--replay, --firewall)
│   ├── attacker.py                          ← Atacante gemelo Python (Linux/Mac)
│   ├── attacker.ps1                         ← Atacante PowerShell nativo (Windows)
│   ├── Launcher.ps1                         ← Kit rol-aware (Sensor/Atacante/Operador) + auto-firewall
│   ├── Iniciar.bat                          ← Doble clic → lanza el Launcher
│   ├── LEEME.txt                            ← Guía rápida por rol
│   ├── events_replay.json                   ← Ataque pregrabado (demo sin red)
│   └── README.md                            ← Runbook de la demo
│
└── frontend/
    ├── Dockerfile                           ← Solo para dev local
    ├── vercel.json                          ← Framework vite + rewrites SPA
    ├── package.json
    ├── vite.config.js                       ← proxy /api → http://backend:8000 (solo dev)
    └── src/
        ├── main.js
        ├── App.vue
        ├── styles/
        │   └── global.css                   ← Tokens CSS, Inter, grain texture, componentes base
        ├── plugins/
        │   ├── vuetify.js                   ← Tema claro (blanco/negro/gris)
        │   └── axios.js                     ← baseURL desde VITE_API_BASE_URL + interceptor JWT
        ├── router/index.js                  ← Rutas protegidas por auth y por rol
        ├── stores/
        │   ├── auth.js                      ← login/logout, tokens en localStorage
        │   └── incidents.js                 ← CRUD incidentes, métricas, comentarios, planes
        ├── views/
        │   ├── LoginView.vue                ← Split layout: panel negro + formulario blanco
        │   ├── DashboardView.vue            ← KPI cards + barras por tipo/criticidad/estado
        │   ├── OperationsView.vue           ← Centro de Operaciones en vivo (poll feed 2s)
        │   ├── incidents/
        │   │   ├── IncidentListView.vue     ← Tabla con filtros en tiempo real
        │   │   ├── IncidentCreateView.vue
        │   │   └── IncidentDetailView.vue   ← Historial, plan de acción, comentarios
        │   └── reports/ReportsView.vue      ← Filtros + descarga PDF
        └── components/
            ├── layout/
            │   ├── AppLayout.vue
            │   ├── AppNavbar.vue            ← Barra superior fija (52px)
            │   └── AppSidebar.vue           ← Nav lateral (224px)
            └── incidents/
                ├── StatusChip.vue           ← Dot indicador por estado
                └── CriticalityChip.vue      ← Escala de grises (bajo→crítico=negro)
```

---

## Dominio del modelo

### Roles
| Valor DB | Descripción | Permisos |
|----------|-------------|----------|
| `admin_ti` | Administrador TI | Todo: usuarios, asignación, gestión completa |
| `analista` | Analista de Seguridad | Gestiona incidentes y el checklist; avanza hasta `resuelto` (no puede cerrar) |
| `jefe_area` | Jefe de Área | Lectura + **valida el cierre** (`resuelto → cerrado`); no edita campos |

### Ciclo de vida de un incidente (RF5)
```
abierto → en_investigacion → resuelto → cerrado
         (analista)           (analista)   (jefe_area / admin_ti = validación)
```
Flujo unidireccional. Un incidente `cerrado` no puede modificarse (RNF8). Cada cambio de estado crea un registro `IncidentStatusHistory` inmutable.

**Workflow por rol (V1.1)** — responde a la crítica "los roles no están claros". El cierre es una **validación**: solo `jefe_area` o `admin_ti` pueden pasar de `resuelto` a `cerrado`, y `jefe_area` no puede tocar ningún otro campo. Se enforza en `IncidentUpdateSerializer.validate()` + permiso `CanUpdateOrValidateIncident`.

**SLA automático (V1.1)** — el plazo ya no se digita: se deriva de la criticidad (`incidents/sla.py`): crítico 4h · alto 24h · medio 72h · bajo 168h. Estado calculado contra el historial: `en_plazo` / `en_riesgo` / `vencido` / `cumplido` / `incumplido`. Expuesto en `GET /api/incidents/{id}/` (campo `sla`).

**Plan de acción = checklist (V1.1)** — `ActionPlan.steps` pasó de `list[str]` a `list[{text, done, done_by, done_at, evidence}]`. Marcar un paso sella quién/cuándo en el servidor (no se confía en el cliente). El plan se expone anidado en el detalle del incidente (`action_plan` con `progress`).

### Tipos de incidente
`malware` · `acceso_no_autorizado` · `phishing` · `fuga_datos` · `fallo_configuracion` · `otro`

### Criticidades
`bajo` · `medio` · `alto` · `critico`

---

## API — Endpoints principales

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/api/auth/login/` | JWT access + refresh. Respuesta incluye objeto `user` |
| `POST` | `/api/auth/token/refresh/` | Renueva access token |
| `GET` | `/api/auth/me/` | Usuario autenticado |
| `GET/POST` | `/api/auth/users/` | Listar / crear usuarios (solo `admin_ti`) |
| `GET` | `/api/incidents/` | Listar incidentes (paginado + filtros) |
| `POST` | `/api/incidents/` | Crear incidente → genera plan de acción automático |
| `GET` | `/api/incidents/{id}/` | Detalle con historial, comentarios y plan |
| `PATCH` | `/api/incidents/{id}/` | Actualizar o cambiar estado |
| `POST` | `/api/incidents/{id}/comments/` | Agregar comentario |
| `GET` | `/api/incidents/dashboard/` | Métricas del dashboard |
| `GET/PATCH` | `/api/action-plans/{id}/` | Ver / editar plan de acción |
| `GET` | `/api/reports/pdf/` | Exportar PDF (acepta mismos filtros que `/incidents/`) |
| `POST` | `/api/ingest/events/` | Ingesta de un evento del sensor — **autentica con `X-API-Key`** (no JWT) |
| `GET` | `/api/ingest/feed/` | Estado en vivo del Centro de Operaciones (counts + eventos + incidentes + IPs contenidas) |
| `GET` | `/api/ingest/blocklist/` | IPs en contención activa (**`X-API-Key`**) — el sensor la consulta y la aplica (SOAR) |

### Cambio de estado via PATCH
```json
{ "new_status": "en_investigacion", "status_comment": "Iniciando análisis forense." }
```

### Filtros en `/api/incidents/`
`status`, `criticality`, `incident_type`, `affected_area__icontains`, `assigned_to`, `created_by`, `detected_from`, `detected_to`, `search`

---

## Mini-SIEM (V1.1) — detección automática de incidentes

Responde a la crítica del docente ("muy simple" + "el encargado no debería crear los incidentes a mano"): los incidentes ahora se generan **solos** a partir de eventos de red. Todo construido sin librerías de terceros (motor de reglas propio, sensor y atacante en stdlib) para poder explicarlo línea por línea.

```
atacante → (TCP) → sensor → (HTTP + X-API-Key) → /api/ingest/events/
                                                        │
                                         motor de reglas (apps/ingest/detection.py)
                                                        │
                                  Incidente automático (reusa generate_action_plan)
                                                        │
                                       Centro de Operaciones (frontend, en vivo)
```

- **App `ingest`** — no toca nada de la V1. `SecurityEvent` guarda el evento crudo; `detection.py` lo evalúa.
- **3 reglas** (umbrales en `detection.py`): `port_scan` (≥8 puertos/30s), `brute_force` (≥5 logins fallidos/60s), `blacklist_ip` (IP en `INGEST_BLACKLIST`).
- Incidentes auto-creados por el usuario de sistema **`sensor`** (sin contraseña usable). Anti-duplicados: un incidente abierto por par (regla, IP).
- **Auth del endpoint de ingesta:** clave estática `INGEST_API_KEY` en cabecera `X-API-Key` (comparación en tiempo constante), sin JWT ni CSRF. El feed sí va con JWT.
- **Demo:** ver `tools/README.md`. Garantía a prueba de firewall del salón → `python tools/sensor.py --replay --target <backend>`.

```bash
docker compose exec backend python manage.py test apps.ingest   # tests del motor
```

### Respuesta activa / contención (V1.2 — salto SIEM→SOAR)

Detectar no basta: al disparar una regla, el motor **contiene** la amenaza. `_fire()` (en `detection.py`) llama a `_contain()`, que da de alta la IP atacante en el modelo **`BlockedIP`** (lista de bloqueo) y anota la contención en el historial del incidente. La contención es **idempotente** (anti-duplicados por IP).

El **punto de aplicación** es el propio **sensor** (no el firewall físico, para poder demostrarlo sobre la LAN del salón sin tocar la red): consulta `GET /api/ingest/blocklist/` cada 2 s y, en cuanto una IP está activa, **corta toda conexión entrante** de esa IP (RST). El atacante ve su conexión caer **en vivo** → eso es lo proyectable.

```
detecta (regla) → BlockedIP (backend decide) → sensor consulta blocklist → corta al atacante (enforce)
```

El Centro de Operaciones muestra las IPs contenidas (KPI "IPs contenidas" + panel "Contención automática (SOAR)").

### Notificación por email (V1.2 — paso "Notificar" del playbook)

Al crearse un incidente automático, `apps/ingest/notifications.py` envía un **email de alerta** profesional (sin emojis) al `SOAR_ALERT_EMAIL`. Es **best-effort**: corre en un hilo daemon y cualquier fallo se loguea, **nunca** rompe la ingesta.

- **Anti-saturación (Opción A — digest por ventana):** el modelo singleton **`AlertThrottle`** (en BD, fila `pk=1`, consistente entre workers de gunicorn) hace que el **primer** incidente de una ráfaga notifique al instante; los siguientes dentro de `SOAR_ALERT_WINDOW_SECONDS` (default 300 s) se **acumulan** y se resumen en el próximo correo. Decisión atómica con `select_for_update`; el envío SMTP/HTTP va **fuera** de la transacción. `reset_demo` limpia el throttle.
- **Envío por HTTP (Resend), NO SMTP — crítico:** **Railway bloquea los puertos SMTP de salida** (25/465/587), así que cualquier backend SMTP da `TimeoutError [Errno 110] Connection timed out`. Se envía por la **API HTTP de Resend** (puerto 443) con el backend custom **`apps/ingest/resend_email.py`** (`ResendEmailBackend`, solo stdlib). Detalle: hay que mandar un **`User-Agent` propio** o Cloudflare (escudo de Resend) responde `403 error 1010`.
  - Existe además `apps/ingest/ipv4_email.py` (`IPv4EmailBackend`): fuerza IPv4 para SMTP. Quedó como referencia, pero **no resuelve** el bloqueo de SMTP de Railway; el camino bueno es Resend.
- **Resend free sin dominio propio** solo envía **a la dirección con la que te registraste** (por eso la cuenta se registró con `leopb77@gmail.com`). Para enviar a otros destinatarios habría que verificar un dominio en Resend.
- **Tests:** `apps.ingest` (21 tests) cubre detección, contención, throttle, release, reset y los dos backends de email.

### Entorno DEV en la nube (Railway + Vercel) — para pruebas sin tocar producción

V1.2 se prueba en un **entorno dev aislado**, duplicado de producción; `main`/producción no se tocan.

| Servicio | URL dev |
|----------|---------|
| Backend dev (Railway) | https://backend-dev-6d4d.up.railway.app |
| Frontend dev (Vercel) | https://sgis-ucv-git-dev-awoo-cs-projects.vercel.app (Deployment Protection desactivado para que la demo abra sin login de Vercel) |

- El entorno dev de Railway (id `2e721939-19a2-4c7b-8fd4-eeaf10c3cc06`) tiene su **propio Postgres**; sus vars de DB deben ser **referencias** (`${{Postgres.POSTGRES_PASSWORD}}`, etc.), no copias del de producción.
- Deploy del backend dev: `railway up ./backend --path-as-root --service backend --environment dev --detach`.
- El frontend dev **debe** llevar `VITE_API_BASE_URL` apuntando al backend dev **con sufijo `/api`** (el front pega `/auth/login/` sobre la base).

---

## Diseño del frontend

**Estética:** "Swiss Editorial Minimal" — blanco/negro/gris, fuente Inter.

- `global.css` → tokens CSS, grain texture 3.5%, componentes `.kpi-card`, `.bar-row`, `.section-label`
- `vuetify.js` → tema claro, primary = `#0A0A0A`
- Login: split layout (panel negro izquierdo / formulario blanco derecho)
- Dashboard: KPI números Inter ExtraBold 3.75rem, barras de 2px, skeletons en carga
- Sidebar: ítem activo = inversión negro/blanco
- StatusChip: dot indicador coloreado · CriticalityChip: escala de grises

---

## Convenciones de código

- **Python:** PEP 8, lógica de negocio en models/serializers
- **Vue:** Composition API con `<script setup>`, CSS scoped, variables CSS globales
- **Git:** trabajar en `dev`, merge a `main` solo con permiso explícito del equipo
- **Commits:** sin `Co-Authored-By: Claude`

---

## Comandos útiles

```bash
# ── Desarrollo local ─────────────────────────────────────────────
docker compose up --build                                  # levantar todo
docker compose logs backend -f                             # logs en tiempo real
docker compose exec backend python manage.py shell         # Django shell
docker compose exec backend python manage.py create_demo_data --clear  # resetear datos demo

# ── Railway (producción) ─────────────────────────────────────────
export PATH="$HOME/.railway/bin:$PATH"
railway up ./backend --path-as-root --service backend --detach -m "descripción"
railway logs --service backend --lines 50
railway service list --json

# ── Vercel (frontend) ────────────────────────────────────────────
# desde frontend/:
VERCEL_TOKEN=<token> npx vercel --prod --token <token> --yes --scope awoo-cs-projects

# ── Git ──────────────────────────────────────────────────────────
git checkout dev && git add . && git commit -m "feat: ..."
git push origin dev
```
