# SGIS-UCV — Sistema de Gestión de Incidentes de Seguridad

Plataforma web para el Centro de Cómputo de la Universidad César Vallejo (UCV). Registra, clasifica, asigna, da seguimiento y cierra incidentes de ciberseguridad, con planes de acción automáticos y exportación de reportes PDF.

**Curso:** Redes y Seguridad Perimetral — 2026  
**Docente:** Mgtr. Soldi Escobar, Emilio Cesar Nicolas  
**Equipo:** Castillo Valverde J., Chuquitapa Pérez S., Lazarte Moreno R., Liñan Huanca J., Pizarro Bordoy L.

---

## Stack

| Capa | Tecnología |
|------|-----------|
| Frontend | Vue.js 3 + Vuetify 3 + Pinia + Vue Router 4 + Axios |
| Backend | Django 4.2 + Django REST Framework 3.15 + SimpleJWT |
| Base de datos | PostgreSQL 16 |
| Contenedores | Docker + Docker Compose |
| Reportes | ReportLab (PDF) |

---

## Levantar el proyecto

```bash
cd sgis-ucv
cp .env.example .env          # solo la primera vez
docker compose up --build     # construye imágenes y levanta los 3 servicios
```

El backend corre `makemigrations` + `migrate` + `loaddata` automáticamente en cada arranque.

| Servicio | URL |
|----------|-----|
| Frontend (Vue) | http://localhost:5173 |
| Backend (API) | http://localhost:8000 |
| Django Admin | http://localhost:8000/admin |

**Reinicio limpio** (borra la base de datos):
```bash
docker compose down -v && docker compose up --build
```

---

## Usuarios de prueba (cargados automáticamente)

| Usuario | Contraseña | Rol |
|---------|-----------|-----|
| `admin.ti` | `Sgis2026*` | Administrador TI — acceso total + Django admin |
| `analista` | `Sgis2026*` | Analista de Seguridad — crear/gestionar incidentes |
| `jefe.area` | `Sgis2026*` | Jefe de Área — solo lectura y dashboard |

Los usuarios se crean desde `backend/initial_data.json` vía `loaddata`.

---

## Estructura de archivos

```
sgis-ucv/
├── docker-compose.yml
├── .env / .env.example
├── CLAUDE.md
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── manage.py                        ← DJANGO_SETTINGS_MODULE = sgis.settings.development
│   ├── initial_data.json                ← Fixture con usuarios seed
│   ├── sgis/
│   │   ├── settings/
│   │   │   ├── base.py                  ← Config principal (DB, JWT, DRF, CORS)
│   │   │   └── development.py           ← DEBUG=True, CORS_ALLOW_ALL_ORIGINS=True
│   │   ├── urls.py                      ← Rutas raíz + inclusión de apps
│   │   └── wsgi.py
│   └── apps/
│       ├── accounts/                    ← CustomUser + JWT custom + permisos por rol
│       │   ├── models.py                ← CustomUser (AbstractUser + campo role)
│       │   ├── serializers.py           ← CustomTokenObtainPairSerializer, UserSerializer
│       │   ├── views.py                 ← Login, /me/, CRUD usuarios
│       │   ├── urls.py
│       │   └── permissions.py           ← IsAdminTI, IsAdminTIOrAnalista, IsJefeArea
│       ├── incidents/                   ← Núcleo del sistema
│       │   ├── models.py                ← Incident, IncidentStatusHistory, IncidentComment
│       │   ├── serializers.py           ← List / Detail / Create / Update (con cambio de estado)
│       │   ├── views.py                 ← CRUD + endpoint dashboard_metrics
│       │   ├── filters.py               ← IncidentFilter (django-filter)
│       │   └── urls.py
│       ├── action_plans/                ← Planes de acción automáticos (RF6)
│       │   ├── models.py                ← ActionPlan (OneToOne → Incident)
│       │   ├── plan_templates.py        ← Plantillas por tipo × criticidad
│       │   ├── serializers.py
│       │   ├── views.py
│       │   └── urls.py
│       └── reports/                     ← Exportación PDF (RF9)
│           ├── pdf_generator.py         ← ReportLab: tabla coloreada por criticidad
│           ├── views.py                 ← GET /api/reports/pdf/ con filtros
│           └── urls.py
│
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── vite.config.js                   ← proxy /api → http://backend:8000
    └── src/
        ├── main.js                      ← App + Pinia + Router + Vuetify + global.css
        ├── App.vue
        ├── styles/
        │   └── global.css               ← Tokens CSS, tipografía Inter, componentes base
        ├── plugins/
        │   ├── vuetify.js               ← Tema claro: blanco/negro/gris + Inter
        │   └── axios.js                 ← baseURL + interceptor JWT (refresh automático)
        ├── router/
        │   └── index.js                 ← Rutas protegidas por auth y por rol
        ├── stores/
        │   ├── auth.js                  ← login/logout, tokens en localStorage
        │   └── incidents.js             ← CRUD incidentes, métricas, comentarios, planes
        ├── views/
        │   ├── LoginView.vue            ← Split layout: panel negro + formulario blanco
        │   ├── DashboardView.vue        ← KPI cards + barras por tipo/criticidad/estado
        │   ├── incidents/
        │   │   ├── IncidentListView.vue ← Tabla con filtros en tiempo real
        │   │   ├── IncidentCreateView.vue
        │   │   └── IncidentDetailView.vue ← Historial, plan de acción editable, comentarios
        │   └── reports/
        │       └── ReportsView.vue      ← Filtros + descarga PDF directa
        └── components/
            ├── layout/
            │   ├── AppLayout.vue        ← Shell: Navbar + Sidebar + main
            │   ├── AppNavbar.vue        ← Barra superior fija (52px)
            │   └── AppSidebar.vue       ← Navegación lateral (224px)
            └── incidents/
                ├── StatusChip.vue       ← Chip con dot indicador por estado
                └── CriticalityChip.vue  ← Chip escala de grises (bajo→crítico=negro)
```

---

## Dominio del modelo

### Roles
| Valor DB | Descripción | Permisos |
|----------|-------------|----------|
| `admin_ti` | Administrador TI | Crear/editar usuarios, asignar responsables, todo |
| `analista` | Analista de Seguridad | Crear y gestionar incidentes, editar planes |
| `jefe_area` | Jefe de Área | Solo lectura — dashboard y reportes |

### Estados del ciclo de vida (RF5)
```
abierto → en_investigacion → resuelto → cerrado
```
Flujo unidireccional. Un incidente `cerrado` no puede modificarse (RNF8). Cada cambio de estado genera un `IncidentStatusHistory` inmutable.

### Tipos de incidente
`malware` · `acceso_no_autorizado` · `phishing` · `fuga_datos` · `fallo_configuracion` · `otro`

### Criticidades
`bajo` · `medio` · `alto` · `critico`

---

## API — Endpoints principales

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/api/auth/login/` | Obtiene `access` + `refresh` JWT. Respuesta incluye objeto `user` |
| `POST` | `/api/auth/token/refresh/` | Renueva access token |
| `GET` | `/api/auth/me/` | Usuario autenticado |
| `GET/POST` | `/api/auth/users/` | Listar / crear usuarios (solo `admin_ti`) |
| `GET` | `/api/incidents/` | Listar incidentes (paginado, filtros por query param) |
| `POST` | `/api/incidents/` | Crear incidente → genera plan de acción automático |
| `GET` | `/api/incidents/{id}/` | Detalle completo con historial, comentarios y plan |
| `PATCH` | `/api/incidents/{id}/` | Actualizar campos o cambiar estado (`new_status` + `status_comment`) |
| `POST` | `/api/incidents/{id}/comments/` | Agregar comentario |
| `GET` | `/api/incidents/dashboard/` | Métricas: total, críticos activos, por estado/tipo/criticidad |
| `GET/PATCH` | `/api/action-plans/{id}/` | Ver / editar pasos del plan de acción |
| `GET` | `/api/reports/pdf/` | Descargar PDF. Soporta los mismos filtros que `/api/incidents/` |

### Filtros disponibles en `/api/incidents/`
`status`, `criticality`, `incident_type`, `affected_area__icontains`, `assigned_to`, `created_by`, `detected_from`, `detected_to`, `search` (título, descripción, área)

### Cambio de estado via PATCH
```json
{ "new_status": "en_investigacion", "status_comment": "Iniciando análisis forense." }
```

### JWT — estructura del token
El access token incluye claims extra: `username`, `role`, `full_name`. El axios interceptor renueva el token automáticamente en 401 y redirige a `/login` si el refresh también expiró.

---

## Planes de acción automáticos (RF6)

Al crear un incidente, `apps/action_plans/plan_templates.py` genera pasos estándar según `incident_type` × `criticality`. Los incidentes críticos reciben pasos adicionales de escalamiento al inicio.

Para modificar o añadir plantillas editar el diccionario `_STEPS` en `plan_templates.py`. No requiere migración.

---

## Variables de entorno (`.env`)

```bash
# PostgreSQL
POSTGRES_DB=sgis_db
POSTGRES_USER=sgis_user
POSTGRES_PASSWORD=sgis_pass
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Django
SECRET_KEY=<clave-secreta-larga>
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,backend

# JWT
ACCESS_TOKEN_LIFETIME_MINUTES=60
REFRESH_TOKEN_LIFETIME_DAYS=7

# Frontend
VITE_API_BASE_URL=http://localhost:8000/api
```

---

## Diseño del frontend

**Estética actual:** "Swiss Editorial Minimal" — blanco/negro/gris, fuente Inter.

- `src/styles/global.css` — tokens CSS (`--bg`, `--white`, `--black`, `--ink-*`, `--border`), grain texture al 3.5%, componentes base (`.kpi-card`, `.bar-row`, `.section-label`, `.status-block`)
- `src/plugins/vuetify.js` — tema claro personalizado; primary = `#0A0A0A`
- Login: split layout (panel negro izquierdo / formulario blanco derecho)
- Dashboard: KPI numbers en Inter ExtraBold 3.75rem; barras de 2px negras; skeletons en carga
- Ítem activo en sidebar: inversión negro/blanco
- `StatusChip`: dot indicador coloreado por estado
- `CriticalityChip`: escala de grises — Bajo=gris claro, Crítico=negro sólido

Para cambiar el diseño, editar `global.css` y `vuetify.js`. Los componentes usan variables CSS, no colores hardcodeados.

---

## Gotchas conocidos

| Problema | Causa | Solución |
|----------|-------|----------|
| `docker compose` no encontrado | Plugin no instalado | `sudo pacman -S docker-compose` |
| `permission denied /var/run/docker.sock` | Daemon no activo o usuario sin grupo | `sudo systemctl start docker` · `sudo usermod -aG docker $USER` |
| `database "sgis_user" does not exist` en logs de DB | Healthcheck sin `-d` — ya corregido | Ruido inofensivo del healthcheck; no afecta el sistema |
| 500 en login tras primer arranque | Tablas aún no creadas (migrate en curso) | Esperar ~20s; el backend corre `makemigrations` antes del `runserver` |
| El volumen `pgdata` tiene datos de un arranque anterior incorrecto | Variables de entorno cambiaron | `docker compose down -v` para reiniciar la DB desde cero |
| `loaddata` falla silenciosamente | Tablas ya tienen los PKs (arranques repetidos) | Comportamiento esperado; el `|| true` en el comando lo ignora |

---

## Convenciones de código

- **Python:** PEP 8, sin comentarios innecesarios, lógica de negocio en models/serializers no en views
- **Vue:** Composition API con `<script setup>`, CSS scoped por componente, variables CSS globales para colores
- **Git:** trabajar en rama `dev`, merge a `main` solo cuando el profesor lo indique explícitamente
- **Commits:** sin `Co-Authored-By: Claude`

---

## Comandos útiles

```bash
# Ver logs en tiempo real
docker compose logs backend -f
docker compose logs frontend -f

# Ejecutar comandos Django dentro del contenedor
docker compose exec backend python manage.py shell
docker compose exec backend python manage.py createsuperuser

# Regenerar migraciones (si se modifica un modelo)
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py migrate

# Instalar nueva dependencia Python
# 1. Agregar a requirements.txt
# 2. docker compose up --build  (reconstruye la imagen)
```
