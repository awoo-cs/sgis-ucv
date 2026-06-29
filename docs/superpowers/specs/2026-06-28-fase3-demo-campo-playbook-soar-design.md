# SGIS-UCV — Fase 3 (Demo de Campo): Playbook SOAR + Kit de despliegue

- **Fecha:** 2026-06-28
- **Estado:** Diseño aprobado por Leo → pendiente plan de implementación.
- **Motiva:** Próximo avance con el docente sobre **red propia** (router + switch + 3-4 laptops de compañeros, **W11 nativo**, sin la PC del salón). Dos cosas que resolver, planteadas por Leo:
  1. *"Una vez bloqueada la IP, si el profe quiere repetir la demo, ¿dónde se desbloquea?"*
  2. *"Solo bloquear la IP me parece básico — ¿qué otra cosa más podríamos hacer para impresionar?"*
  - Y un tercer pedido: **desplegar fácil** cada rol en laptops ajenas el día de la demo.
- **Objetivo en una frase:** convertir la contención de **una sola acción** en un **playbook SOAR orquestado** (Detectar → Contener → **Notificar** → Documentar → **Revisar/Liberar**), y entregar un **kit** que arranca cada rol en su laptop con un clic.

---

## 0. Punto de partida (lo que YA existe en el código)

> El spec previo (`2026-06-26-respuesta-activa-soar-design.md`) propuso un modelo genérico `ResponseAction` + middleware Django + blindaje del login. **Eso NO se construyó así.** Se implementó una versión más simple y suficiente (ponytail), que es la base real sobre la que monta este avance:

- `apps/ingest/models.py::BlockedIP` — lista de contención (una fila por IP: `active`, `released_at`, FK al `incident`).
- `apps/ingest/detection.py` — `evaluate()` → `_fire()` → `_contain()`. `_contain` es idempotente y anota la contención en el `IncidentStatusHistory`.
- `apps/ingest/views.py` — `EventIngestView` (X-API-Key), `BlocklistView` (GET, X-API-Key), `OperationsFeedView` (JWT, ya devuelve `counts` + `blocked_ips`).
- `tools/sensor.py` — consulta `/blocklist/` cada 2s y **corta a nivel app** (RST) las IPs activas.
- `frontend/src/views/OperationsView.vue` — panel "Contención automática (SOAR)" + KPI "IPs contenidas".

Este avance **extiende** esa base. **No** introduce `ResponseAction` (sigue siendo YAGNI: el playbook se arma sobre `BlockedIP` + el incidente).

## 1. Topología de la demo (decidida)

- **Backend** = Railway (nube) · **tablero** = Vercel. **Ningún laptop instala Docker.**
- El **corte en vivo ocurre en la LAN** (lo aplica el sensor), aunque el cerebro esté en la nube. La IP del atacante la captura el sensor localmente (`addr[0]`), así que es la IP LAN real de punta a punta.
- Único requisito de red: internet en el router (hotspot del celular como respaldo).

**Reparto roles ↔ laptops** (4 laptops: 2 controlables de compañeros de grupo + 2 ajenas sin control hasta el día):

| Laptop | Rol | ¿Instala? | Por qué ahí |
|---|---|---|---|
| Controlable #1 | **Sensor** | Python (pre-instalado) | Único rol que necesita algo → donde hay control |
| Ajena #1 | **Atacante** | Nada (`attacker.ps1` nativo) | PowerShell ya viene en W11 |
| Ajena #2 | **Operador** (proyecta) | Nada (navegador) | Solo abre el tablero |
| Controlable #2 | **Sensor de respaldo** | Python (por si acaso) | Seguro anti-fallo del rol sensible |

**Regla de oro:** lo que necesita instalar va en TUS laptops; lo cero-install va en las ajenas.

## 2. La estrella polar: el guion (beats)

| Beat | Qué pasa en pantalla |
|------|----------------------|
| 0 | Sensor escuchando (laptop tuya), atacante (laptop ajena), Operador proyecta el **Centro de Operaciones**. |
| 1 | El atacante lanza *Ataque completo*. **Nadie toca el SGIS.** |
| 2 | En 2-3s aparece **solo** un incidente rojo. *"Nadie lo creó; el sistema lo vio."* |
| 3 | **🛡️ CONTENIDO** — la IP entra a la lista de bloqueo. |
| 4 | El **email** llega al celu del "equipo SOC" → *"y además, notifica al equipo, como un SOC real"*. |
| 5 | El atacante reintenta → **conexión rechazada** (corte app + **regla de Windows Firewall real** en el sensor). Está afuera de verdad. |
| 6 | En el tablero, el operador pulsa **"Liberar"** → en ≤2s el atacante **vuelve a conectarse** (de-contención revisada por un humano). |
| 7 | **"Reiniciar demo"** deja el tablero en blanco → se repite cuantas veces el profe quiera. |

El playbook se muestra en el tablero como **pasos que se marcan ✓** por cada IP contenida. *Bloquear la IP es 1 de 5 pasos, no el final.*

## 3. Backend (`apps/ingest`)

### 3.1 Notificar por email (paso "Notificar")
- Nuevo módulo `apps/ingest/notifications.py`:
  ```python
  def send_incident_alert(incident):
      """Envía el correo de alerta. Best-effort: cualquier fallo se loguea y NO rompe nada."""
      # django.core.mail.send_mail(subject, body, from, [SOAR_ALERT_EMAIL], fail_silently=False)
  def dispatch_incident_alert(incident):
      """Lo dispara en un hilo daemon para NO bloquear la ingesta."""
      threading.Thread(target=_safe, args=(incident,), daemon=True).start()
  ```
- **Enganche:** en `detection.py::_fire`, **solo cuando el incidente es nuevo** (`created`), tras `_contain(...)`, llamar `dispatch_incident_alert(incident)`. En incidentes reusados (anti-dup) no se re-notifica.
- **Asunto:** `[SGIS-UCV] 🚨 {criticality} — {title}`. **Cuerpo:** tipo, criticidad, IP, sensor, hora, regla, link al detalle.
- **Settings** (`base.py`, vía `decouple.config`, defaults seguros para dev):
  ```python
  EMAIL_BACKEND      = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
  EMAIL_HOST         = config('EMAIL_HOST', default='smtp.gmail.com')
  EMAIL_PORT         = config('EMAIL_PORT', default=587, cast=int)
  EMAIL_USE_TLS      = config('EMAIL_USE_TLS', default=True, cast=bool)
  EMAIL_HOST_USER    = config('EMAIL_HOST_USER', default='')
  EMAIL_HOST_PASSWORD= config('EMAIL_HOST_PASSWORD', default='')
  DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='SGIS-UCV <no-reply@sgis.local>')
  SOAR_ALERT_EMAIL   = config('SOAR_ALERT_EMAIL', default='leopb77@gmail.com')
  ```
  - **Dev:** backend `console` → el correo se imprime en el log (probar sin SMTP real).
  - **Demo (Railway):** Leo pone `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, `EMAIL_HOST_USER`=su Gmail, `EMAIL_HOST_PASSWORD`=**app password** de Gmail.

### 3.2 Señal del playbook: `alerted_at`
- Añadir `BlockedIP.alerted_at = DateTimeField(null=True, blank=True)`. Se setea al disparar el email. El feed lo expone → el tablero pinta el paso **Notificar ✓**. (Los demás pasos se infieren de que el `BlockedIP` exista.)

### 3.3 Liberar contención (paso "Revisar/Liberar")
- Nueva vista `ReleaseBlockView` → `POST /api/ingest/blocklist/<source_ip>/release/`, **JWT** (`analista` o `admin_ti`).
  - `active=False`, `released_at=now`; anota en el historial del incidente *"Contención levantada por {user}"*.
  - Al salir de `BlockedIP.objects.filter(active=True)`, la IP desaparece de `/blocklist/` → el sensor la suelta en ≤2s (abre puerta + borra regla de firewall).

### 3.4 Reiniciar demo
- Helper `reset_demo_data()` (en `apps/ingest/maintenance.py`): borra **solo** lo del sensor — todos los `SecurityEvent`, todos los `BlockedIP`, y los `Incident` cuyo `created_by` sea el usuario `sensor` (cascada: historial, plan, blocked_ips). **Respeta** los 45 demo y los incidentes manuales. Devuelve el conteo de lo borrado.
- `apps/ingest/management/commands/reset_demo.py` → llama al helper (uso CLI / Railway).
- Vista `ResetDemoView` → `POST /api/ingest/reset/`, **JWT solo `admin_ti`** → llama al helper (botón del operador). El operador inicia sesión como `admin.ti` el día de la demo.

### 3.5 Feed
- `OperationsFeedView` y `BlockedIPSerializer`: incluir `alerted_at`, `incident` (id) y `created_at` por IP, para que el tablero arme el playbook y el "tiempo de reacción".

## 4. Sensor (`tools/sensor.py`) — firewall real (paso "Contener", capa 2)

Hoy el sensor corta a nivel app (RST). Se le agrega **enforcement a nivel SO en Windows** con `netsh`, manteniendo el RST como base que **siempre** funciona.

- Mantener la blocklist como `set`. En cada poll, calcular el **diff**: IPs nuevas y IPs retiradas (reconcile declarativo).
- **IP nueva** → además del deny-set en memoria, si `--firewall` y es Windows con admin:
  `netsh advfirewall firewall add rule name="SGIS-block-<ip>" dir=in action=block remoteip=<ip>`
- **IP retirada** (liberada) → sacar del deny-set + `netsh advfirewall firewall delete rule name="SGIS-block-<ip>"`.
- **Flag `--firewall`**: lo pasa el launcher en "Iniciar sensor (firewall real)". Si se pide pero no hay admin / no es Windows → **warning y fallback** a solo-app (la demo nunca depende de tener admin).
- **Detección de admin (Windows):** `ctypes.windll.shell32.IsUserAnAdmin()`.
- **Higiene:** al salir (Ctrl-C / `finally`), borrar todas las reglas `SGIS-block-*` que creó (no dejar la laptop con bloqueos colgados).
- *Multiplataforma:* en Linux/Mac (el dev de Leo) `netsh` no existe → se loguea *"firewall real solo en Windows; aquí corto en la app"* y sigue. La lógica del **diff** es una función pura testeable sin tocar `netsh`.

## 5. Frontend (`OperationsView.vue` + `stores/incidents.js`)

- **Playbook por IP contenida:** en el panel "Contención automática (SOAR)", cada IP muestra una fila de pasos: **Detectar ✓ · Contener ✓ · Notificar ✓/⏳ · Documentar ✓ · Revisar/Liberar [botón]**. (Notificar ✓ si `alerted_at`.)
- **Botón "Liberar"** por IP (visible a `analista`/`admin_ti`) → `releaseBlock(ip)` → quita la IP del panel (optimista) + refresca.
- **Botón "Reiniciar demo"** en la cabecera (solo `admin_ti`) → confirm → `resetDemo()` → tablero a cero.
- **Tiempo de reacción** (opcional, barato): `detectado → contenido` por IP, si los timestamps lo permiten.
- Store: `releaseBlock(ip)` → `POST /ingest/blocklist/{ip}/release/`; `resetDemo()` → `POST /ingest/reset/`.

## 6. Kit de Demo (`tools/`) — el "mini-dashboard"

El kit **es la carpeta `tools/`** (se copia entera por USB a cada laptop; el launcher referencia `./sensor.py` y `./attacker.ps1` en su mismo directorio — sin duplicar archivos).

- **`tools/Launcher.ps1`** — GUI **WinForms** (nativa en Windows PowerShell 5.1, cero instalación), **rol-aware**:
  - Selector **"Rol de esta laptop"**: Atacante / Sensor / Operador.
  - Fila de **config** pre-rellenada: URL de Railway + API Key (y, en Atacante, "IP del sensor").
  - **Panel de log** (consola read-only) que **narra** cada acción — para proyectar y explicar.
  - **Botones por rol:**
    - 🔴 **Atacante:** *Verificar objetivo* · *Escaneo de puertos* · *Fuerza bruta* · ***Ataque completo*** (invoca `attacker.ps1` contra la IP del sensor).
    - 🟢 **Sensor:** *Verificar entorno* (¿Python? ¿archivos? ¿Railway responde?) · **"Mi IP LAN: …"** en grande · *Iniciar sensor (firewall real)* / *Iniciar (solo app)* / *Detener* (lanza `python sensor.py --target <Railway> [--firewall]`, su salida al log).
    - 🔵 **Operador:** *Abrir Centro de Operaciones* (navegador) · *Mostrar credenciales* (`admin.ti` / `Sgis2026*`).
- **`tools/Iniciar.bat`** — doble clic → `powershell -ExecutionPolicy Bypass -File Launcher.ps1`. La variante del sensor con firewall real re-lanza elevado (UAC una vez).
- **`tools/LEEME.txt`** — 5 líneas: copia la carpeta · doble clic en `Iniciar.bat` · elige rol · (sensor: ver "Mi IP") · (atacante: teclear esa IP).

## 7. Lo que prepara Leo / lo que verifica Claude

**Leo, antes de la clase:**
1. Internet en el router (hotspot de respaldo).
2. Python en las 2 laptops controlables.
3. Admin en el laptop sensor (para el firewall real; si no, cae a solo-app).
4. SMTP en Railway: `EMAIL_BACKEND` smtp + `EMAIL_HOST_USER` + `EMAIL_HOST_PASSWORD` (app password de Gmail). `SOAR_ALERT_EMAIL` ya default a `leopb77@gmail.com`.

**Claude verifica:** el valor real de `INGEST_API_KEY` en Railway → para pre-rellenarlo como default del launcher.

## 8. Pruebas (estilo `apps/ingest/tests.py`, sin frameworks nuevos)

- **Notificar:** con backend de email `locmem`, un incidente NUEVO encola 1 correo a `SOAR_ALERT_EMAIL`; un evento de dedup **no** re-notifica; si `send_mail` lanza, `evaluate()` igual devuelve su resultado (no rompe). `alerted_at` queda seteado.
- **Liberar:** `POST …/release/` pone `active=False` y la IP **desaparece** de `/blocklist/`; requiere JWT; `jefe_area` no puede.
- **Reiniciar:** `reset_demo_data()` borra eventos/bloqueos/incidentes-del-sensor y **conserva** un incidente manual de control.
- **Sensor (función pura del diff):** dado `desired` vs `current`, calcula bien `to_add` / `to_remove`. Self-check con `assert` (stdlib), sin tocar `netsh`.

## 9. Fuera de alcance (YAGNI)

- Tarpit y deception (se evaluaron; no entran este avance).
- Modelo genérico `ResponseAction`, middleware web de bloqueo, blindaje del login (del spec previo; no se construyeron y no hacen falta para esta demo).
- Notificación por SMS/push (email basta).
- Aplicar reglas en el switch/firewall físico (se aplica en el host vía `netsh`).
- Persistir la blocklist del sensor entre reinicios (se re-sincroniza del servidor).

## 10. Plan por fases

1. **Backend — Notificar + señal:** `notifications.py` (email en hilo), settings de email, `alerted_at` (+ migración), enganche en `_fire`. Tests.
2. **Backend — Liberar + Reiniciar:** `ReleaseBlockView`, `reset_demo_data()` + comando + `ResetDemoView`, rutas, feed con `alerted_at`. Tests.
3. **Sensor — firewall real:** reconcile (diff) + `netsh` add/delete + flag `--firewall` + detección de admin + limpieza al salir. Self-check del diff.
4. **Frontend — playbook + botones:** pasos por IP, botón "Liberar", botón "Reiniciar demo", métodos del store.
5. **Kit — launcher:** `Launcher.ps1` (GUI rol-aware) + `Iniciar.bat` + `LEEME.txt`. Verificar `INGEST_API_KEY` de Railway.
6. **Ensayo:** runbook de los 7 beats en `tools/README.md`; ampliar `events_replay.json` si hace falta para el plan B.
