# SGIS-UCV — Sistema de Gestión de Incidentes de Seguridad

Plataforma web para el Centro de Cómputo de la Universidad César Vallejo. Registra,
clasifica, asigna y da seguimiento a incidentes de ciberseguridad. Más allá de solo
**detectar** (SIEM), el sistema **responde**: al detectar un ataque contiene la amenaza
bloqueando la IP atacante y notifica por email (enfoque SOAR).

> **Curso:** Redes y Seguridad Perimetral — 2026 · **Docente:** Mgtr. Soldi Escobar, Emilio C. N.

---

## Bienvenido/a al equipo — empieza por aquí

Este README es la **puerta de entrada**. Léelo completo; toma ~15 minutos y te ahorra días.

1. **Este archivo (README.md)** → visión general, cómo levantar el proyecto, mapa de carpetas.
2. **[`CLAUDE.md`](CLAUDE.md)** → la **referencia técnica detallada**: cada endpoint, cada regla de
   detección, decisiones de arquitectura, variables de entorno y comandos de despliegue.
   Cuando este README te deje con una duda del tipo "¿y cómo funciona X por dentro?", la
   respuesta está ahí.

---

## ¿Qué hace el sistema? (en una frase por pieza)

| Pieza | Qué hace |
|-------|----------|
| **Gestión de incidentes** | CRUD de incidentes con ciclo de vida (`abierto → en_investigacion → resuelto → cerrado`), roles, SLA automático por criticidad y plan de acción (checklist) auto-generado. |
| **Mini-SIEM (detección)** | Un *sensor* reporta eventos de red; un motor de reglas propio crea incidentes **solos** cuando detecta port-scan, fuerza bruta o IPs en lista negra. |
| **SOAR (respuesta activa)** | Al detectar, el sistema **contiene**: da de alta la IP en una lista de bloqueo que el sensor aplica cortando la conexión del atacante en vivo. Luego **notifica** por email. |
| **Reportes** | Exportación de incidentes a PDF. |

El "por qué" de cada pieza (críticas del docente que resolvió) está en `CLAUDE.md → Estado y roadmap`.

---

## Stack

| Capa | Tecnología |
|------|-----------|
| Frontend | Vue 3 + Vuetify 3 + Pinia + Vue Router + Axios |
| Backend | Django 4.2 + Django REST Framework + SimpleJWT |
| Base de datos | PostgreSQL 16 |
| Entorno local | Docker + Docker Compose |
| Reportes | ReportLab (PDF) |

Frontend en **Vercel**, backend + DB en **Railway**. URLs y detalles de deploy en `CLAUDE.md`.

---

## Levantar el proyecto en local (5 minutos)

Requisito único: **Docker** y **Docker Compose**.

```bash
git clone https://github.com/awoo-cs/sgis-ucv.git
cd sgis-ucv
cp .env.example .env          # solo la primera vez
docker compose up --build     # levanta db + backend + frontend
```

El backend aplica migraciones y carga datos de demo automáticamente. Cuando termine:

| Servicio | URL local |
|----------|-----------|
| Frontend | http://localhost:5173 |
| API backend | http://localhost:8000 |
| Django Admin | http://localhost:8000/admin |

**Reinicio limpio** (borra la base de datos y recarga demo):
```bash
docker compose down -v && docker compose up --build
```

### Usuarios de prueba (ya cargados)

| Usuario | Contraseña | Rol |
|---------|-----------|-----|
| `admin.ti` | `Sgis2026*` | Administrador TI (acceso total) |
| `analista` | `Sgis2026*` | Analista de Seguridad |
| `jefe.area` | `Sgis2026*` | Jefe de Área (valida el cierre) |

---

## Mapa de carpetas

```
sgis-ucv/
├── README.md          ← estás aquí (onboarding)
├── CLAUDE.md          ← referencia técnica completa
├── docker-compose.yml ← orquesta db + backend + frontend en local
│
├── backend/           ← Django + DRF
│   └── apps/
│       ├── accounts/     ← usuarios, JWT y permisos por rol
│       ├── incidents/    ← núcleo: incidentes, historial, SLA
│       ├── action_plans/ ← planes de acción (checklist) automáticos
│       ├── reports/      ← exportación a PDF
│       └── ingest/       ← mini-SIEM + SOAR (detección, contención, email)
│
├── frontend/          ← Vue 3 (código en frontend/src/)
│   └── src/
│       ├── views/        ← pantallas (Login, Dashboard, Operaciones, Incidentes, Reportes)
│       ├── components/   ← piezas reutilizables (layout, chips)
│       ├── stores/       ← estado global (Pinia): auth, incidents
│       └── router/       ← rutas protegidas por auth y rol
│
└── tools/             ← kit de demo (sensor, atacante) — solo stdlib de Python
```

---

## Flujo de trabajo con Git

- Trabajamos siempre en la rama **`dev`**. Nunca se commitea directo a `main`.
- `main` es producción; el merge `dev → main` se hace **solo cuando el docente lo indica**.
- Cada push a `dev` genera automáticamente un preview en Vercel.

```bash
git checkout dev
git pull
# ...tus cambios...
git add . && git commit -m "feat: descripción"
git push origin dev
```

---

## Correr los tests del backend

```bash
docker compose exec backend python manage.py test apps
```

---

## ¿Dónde sigo?

- Detalle de **cada endpoint de la API** → `CLAUDE.md → API — Endpoints principales`.
- Cómo funcionan las **reglas de detección** y la **contención** → `CLAUDE.md → Mini-SIEM`.
- **Deploy** a Vercel/Railway y variables de entorno → `CLAUDE.md → Deployment`.
- Correr la **demo del ataque** (sensor + atacante) → `tools/README.md`.
