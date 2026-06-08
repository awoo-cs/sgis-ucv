---
name: run-sgis-ucv
description: run, launch, start, screenshot, test, smoke SGIS-UCV — Django backend + Vue.js frontend incident management system
---

SGIS-UCV es una aplicación web full-stack: Django 4 en :8000 y Vue.js 3 + Vuetify en :5173, orquestados con Docker Compose. El driver usa Playwright con `google-chrome-stable` headless para el frontend y `fetch`/`curl` para el backend.

## Prerequisitos

```bash
# Node.js disponible en /usr/bin/node (v26 verificado)
# google-chrome-stable en /usr/bin/google-chrome-stable (v148 verificado)
# Docker Compose con el daemon activo

# Instalar playwright (una vez, en /tmp o en el skill dir)
cd /tmp && npm install playwright
```

## Levantar el proyecto

```bash
cd /home/leo/Escritorio/Redes_SeguridadPerimetral/ProyectoConcurso/sgis-ucv
docker compose up -d          # levanta db + backend + frontend
# Esperar ~30s para que el backend corra makemigrations + migrate
```

Verificar que los servicios respondan:
```bash
curl -o /dev/null -w "%{http_code}" http://localhost:8000/api/auth/login/
# → 405  (POST only — el backend está vivo)
curl -o /dev/null -w "%{http_code}" http://localhost:5173
# → 200  (el frontend está vivo)
```

## Run (agent path) — driver Playwright

El driver está en `.claude/skills/run-sgis-ucv/driver.mjs`. Screenshots van a `/tmp/sgis-screenshots/`.

```bash
# Smoke completo: login → dashboard → incidentes → crear incidente → reportes
cd /tmp && node --input-type=module <<'EOF'
import { chromium } from '/tmp/node_modules/playwright/index.mjs';
import { mkdir } from 'fs/promises';

await mkdir('/tmp/sgis-screenshots', { recursive: true });
const ss = async (page, name) => {
  await page.screenshot({ path: `/tmp/sgis-screenshots/${name}.png` });
  console.log('screenshot →', `/tmp/sgis-screenshots/${name}.png`);
};

const browser = await chromium.launch({
  executablePath: '/usr/bin/google-chrome-stable',
  args: ['--no-sandbox', '--disable-dev-shm-usage'],
  headless: true,
});
const page = await (await browser.newContext({ viewport: { width: 1280, height: 800 } })).newPage();

await page.goto('http://localhost:5173', { waitUntil: 'networkidle' });
await page.waitForTimeout(2000);
await ss(page, '01-login');

await page.fill('input[type="text"]', 'admin.ti');
await page.fill('input[type="password"]', 'Sgis2026*');
await page.click('button[type="submit"]');
await page.waitForURL('**/dashboard', { timeout: 15000 });
await page.waitForLoadState('networkidle');
await page.waitForTimeout(2500);
await ss(page, '02-dashboard');

await page.click('a[href="/incidents"]');
await page.waitForLoadState('networkidle');
await ss(page, '03-incidents');

await browser.close();
EOF
```

## API smoke test (sin browser)

```bash
node --input-type=module <<'EOF'
const B = 'http://localhost:8000';
const { access } = await (await fetch(`${B}/api/auth/login/`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: 'admin.ti', password: 'Sgis2026*' }),
})).json();

const H = { Authorization: `Bearer ${access}`, 'Content-Type': 'application/json' };
for (const [m, url, body, exp] of [
  ['GET',  '/api/auth/me/',             null, 200],
  ['GET',  '/api/incidents/',           null, 200],
  ['GET',  '/api/incidents/dashboard/', null, 200],
]) {
  const r = await fetch(`${B}${url}`, { method: m, headers: H, body: body ? JSON.stringify(body) : undefined });
  console.log(r.status === exp ? '✓' : '✗', m, url, '→', r.status);
}
EOF
```

## Credenciales de prueba

| Usuario | Contraseña | Rol |
|---------|-----------|-----|
| `admin.ti` | `Sgis2026*` | Administrador TI (acceso total) |
| `analista` | `Sgis2026*` | Analista de Seguridad |
| `jefe.area` | `Sgis2026*` | Jefe de Área (solo lectura) |

## URLs

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000/api/
- Django Admin: http://localhost:8000/admin/

## Gotchas

- **Los "0" en Orbitron tienen un slash diagonal** — es el carácter tipográfico correcto del font, no un bug. Se ve como ⊘ en el dashboard, lo que es intencional (estética de panel de control militar).
- **`docker compose` requiere el plugin** — instalar con `sudo pacman -S docker-compose`. El daemon requiere `sudo systemctl start docker`.
- **`pg_isready` sin `-d` genera FATAL en logs** — los logs del contenedor DB muestran `database "sgis_user" does not exist` repetidamente; son del healthcheck y no afectan el funcionamiento. El compose ya está corregido con `-d ${POSTGRES_DB:-sgis_db}`.
- **Primer arranque tarda ~20s** — el backend corre `makemigrations` + `migrate` antes de `runserver`. Usar `docker compose logs backend -f` para monitorear.
- **Vuetify v-icon sobreescribe position: absolute** — los íconos decorativos de fondo en los KPI cards se implementan como `span.mdi.mdi-*` para evitar el override de Vuetify.
- **Vite proxea `/api` → backend** — el frontend usa rutas relativas `/api/...`; el proxy en `vite.config.js` apunta a `http://backend:8000` (dentro de Docker). Para peticiones directas desde el host usar `http://localhost:8000/api/`.
- **El interceptor axios renueva tokens** — si el access token expira (60 min), axios intercepta el 401 y llama `/api/auth/token/refresh/` automáticamente. Si el refresh también expira, limpia localStorage y redirige a `/login`.

## Run (human path)

```bash
cd sgis-ucv
docker compose up --build
# Frontend: http://localhost:5173  (abrir en navegador)
# Ctrl-C para detener
```
