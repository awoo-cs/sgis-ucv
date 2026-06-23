# SGIS-UCV — Sistema de Gestión de Incidentes de Seguridad

Plataforma web para el Centro de Cómputo de la Universidad César Vallejo (UCV). Registra, clasifica, asigna, da seguimiento y cierra incidentes de ciberseguridad, con planes de acción automáticos y exportación de reportes PDF.

**Curso:** Redes y Seguridad Perimetral — 2026  
**Docente:** Mgtr. Soldi Escobar, Emilio Cesar Nicolas  
**Equipo:** Castillo Valverde J., Chuquitapa Pérez S., Lazarte Moreno R., Liñan Huanca J., Pizarro Bordoy L.

---

## Estado y roadmap

- **2026-06-17** — Presentada la V1 (demo) al docente. Veredicto: idea buena pero proyecto **muy simple** → hacer una **V1.1 "remasterizada"**.
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
│       └── ingest/                          ← Mini-SIEM V1.1: ingesta + motor de reglas
│           ├── models.py                    ← SecurityEvent (evento crudo del sensor)
│           ├── detection.py                 ← Motor: 3 reglas → incidente automático
│           ├── serializers.py
│           ├── views.py                     ← POST events (API-key) + GET feed (JWT)
│           ├── urls.py
│           └── tests.py                     ← Tests del motor de detección
│
├── tools/                                   ← Demo del mini-SIEM (solo stdlib, sin pip)
│   ├── sensor.py                            ← Honeypot: escucha puertos y reporta (--replay)
│   ├── attacker.py                          ← Atacante gemelo Python (Linux/Mac)
│   ├── attacker.ps1                         ← Atacante PowerShell nativo (Windows)
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
| `analista` | Analista de Seguridad | Crear y gestionar incidentes, editar planes |
| `jefe_area` | Jefe de Área | Solo lectura — dashboard y reportes |

### Ciclo de vida de un incidente (RF5)
```
abierto → en_investigacion → resuelto → cerrado
```
Flujo unidireccional. Un incidente `cerrado` no puede modificarse (RNF8). Cada cambio de estado crea un registro `IncidentStatusHistory` inmutable.

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
| `GET` | `/api/ingest/feed/` | Estado en vivo del Centro de Operaciones (counts + eventos + incidentes) |

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
