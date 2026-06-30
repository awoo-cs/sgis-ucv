# Herramientas del mini-SIEM → SOAR (V1.1 / V1.2)

El bucle completo de la demo (V1.2: ya no solo detecta, **actúa**):

```
atacante → (TCP) → sensor → (HTTP + X-API-Key) → /api/ingest/events/
   ▲                  │                                   │
   │                  │                     motor de reglas (3 reglas)
   │                  │                                   │
   │                  │                  Incidente automático + CONTENCIÓN (bloquea la IP)
   │                  │                                   │
   │            blocklist  ◄───── GET /api/ingest/blocklist/
   │                  │
   └── conexión CORTADA en vivo (el sensor rechaza la IP contenida)
```

Todo es biblioteca estándar: **no hay que instalar nada**.

**V1.2 (salto SIEM→SOAR):** cuando una regla dispara, el motor mete la IP atacante en
una lista de bloqueo. El sensor la consulta cada 2 s y corta toda conexión entrante de
esa IP → el atacante ve caer su conexión en directo. Es la respuesta del profe a
*"¿qué hace el sistema después de detectar?"*.

## Reglas que detecta el motor

| Regla | Se dispara cuando… | Incidente |
|-------|--------------------|-----------|
| `port_scan` | una IP toca ≥8 puertos distintos en 30 s | Acceso no autorizado · medio |
| `brute_force` | una IP genera ≥5 logins fallidos en 60 s | Acceso no autorizado · alto |
| `blacklist_ip` | la IP está en `INGEST_BLACKLIST` | Acceso no autorizado · alto |

(Umbrales en `backend/apps/ingest/detection.py`.)

## 1. Sensor — escucha y reporta

```bash
# Contra el backend local (docker compose arriba)
python tools/sensor.py --target http://localhost:8000

# Contra el backend desplegado en Railway
python tools/sensor.py --target https://backend-production-7cfc1.up.railway.app
```

El sensor abre puertos no privilegiados (no necesita root) y reporta cada conexión.

## 2. Atacante — genera el ataque (otra máquina o la misma)

```bash
# Windows (laptops del equipo, cero instalación):
powershell -ExecutionPolicy Bypass -File tools/attacker.ps1 -Target <IP-del-sensor>

# Linux / Mac (gemelo Python):
python tools/attacker.py --target <IP-del-sensor>
```

Primero escanea puertos, luego hace fuerza bruta. En segundos aparecen 2 incidentes
en el **Centro de Operaciones**.

## 3. Replay — demo enlatada (sin atacante ni red local)

Si la red del salón bloquea todo (pasó en el 1er avance), el sensor reproduce un
ataque pregrabado que dispara las 3 reglas:

```bash
python tools/sensor.py --replay --target https://backend-production-7cfc1.up.railway.app
```

> La clave del sensor sale de `--api-key` o de la variable `INGEST_API_KEY`
> (default `dev-sensor-key-change-me`). En producción debe coincidir con la del backend.

---

# Demo de campo (Fase 3) — playbook SOAR sobre la LAN del salón

El profe pidió pasar de SIEM a **SOAR**: que el sistema no solo detecte, sino que
**responda**. La respuesta no es un solo paso (bloquear la IP) sino un **playbook**:

```
Detectar → Contener → Notificar (email) → Documentar → Revisar/Liberar
```

El tablero (Centro de Operaciones) muestra estos pasos **marcándose ✓ por cada IP
contenida**: bloquear es *1 de 5*, no el final.

## El kit (la forma fácil — sin comandos)

Todo vive en esta carpeta `tools/`. Se copia **entera** (USB) a cada laptop:

1. Doble clic en **`Iniciar.bat`** → abre el launcher (ventana con botones).
2. Elige el **rol de esta laptop**: Atacante / Sensor / Operador.
3. Pega la **API Key real** de la demo (el campo trae la de prueba por defecto;
   debe coincidir con `INGEST_API_KEY` del backend en Railway).

> El launcher NO trae ninguna clave real versionada: por seguridad el default es la
> clave de desarrollo y se reemplaza a mano el día de la demo.

## Reparto roles ↔ laptops (4 laptops)

| Laptop | Rol | Instala | Por qué |
|--------|-----|---------|---------|
| Controlable #1 | **Sensor** | Python (pre-instalado) | Único rol que necesita algo → donde hay control |
| Ajena #1 | **Atacante** | Nada (`attacker.ps1` nativo de W11) | PowerShell ya viene en Windows |
| Ajena #2 | **Operador** (proyecta) | Nada (navegador) | Solo abre el tablero en vivo |
| Controlable #2 | **Sensor de respaldo** | Python | Seguro anti-fallo del rol sensible |

## El guion (beats) — qué se ve en pantalla

| Beat | Qué pasa |
|------|----------|
| 0 | Sensor escuchando (laptop tuya), Operador proyecta el **Centro de Operaciones**. |
| 1 | El atacante pulsa **Ataque completo**. *Nadie toca el SGIS.* |
| 2 | En 2-3 s aparece **solo** un incidente rojo. *"Nadie lo creó; el sistema lo vio."* |
| 3 | **🛡️ CONTENIDO** — la IP entra a la lista de bloqueo (pasos Detectar/Contener en ✓). |
| 4 | Llega el **email** de alerta al equipo → *"y además notifica, como un SOC real"* (paso Notificar ✓). |
| 5 | El atacante reintenta → **conexión rechazada** (corte app + **regla de Windows Firewall real** en el sensor). Está afuera de verdad. |
| 6 | En el tablero, el operador pulsa **Liberar** → en ≤2 s el atacante **vuelve a conectarse** (de-contención revisada por un humano). |
| 7 | **Reiniciar demo** deja el tablero en blanco → se repite cuantas veces el profe quiera. |

`Liberar` lo ven analista/admin; `Reiniciar demo` solo `admin.ti` (el operador inicia
sesión como `admin.ti` / `Sgis2026*`).

## Firewall real en el sensor (paso "Contener", capa 2)

El sensor siempre corta a nivel de aplicación (RST). Con `--firewall` añade, en Windows
con permisos de administrador, una **regla real de Windows Firewall** (`netsh`) por IP:

```bash
python tools/sensor.py --target https://backend-production-7cfc1.up.railway.app --firewall
```

- Reconcilia por **diff** cada 2 s: aplica las IPs nuevas y **levanta** las que el
  operador liberó desde el tablero. Al salir (Ctrl-C) borra sus reglas (no deja basura).
- Si se pide `--firewall` pero no hay admin / no es Windows → **avisa y cae a solo-app**
  (la demo nunca depende de tener admin). El launcher lo lanza elevado (UAC una vez).
- Prueba de la lógica del diff (sin red ni Windows): `python tools/sensor.py --selftest`.

## Lo que Leo prepara antes de la clase

1. **Internet** en el router (con hotspot de respaldo).
2. **Python** en las 2 laptops controlables (rol Sensor).
3. **Admin** en el laptop sensor (el kit pide UAC **una vez** para abrir los puertos
   del sensor en el Firewall de Windows; el firewall real de contención también).
4. **Email por Resend (HTTP, no SMTP)** ya configurado en Railway. OJO: Railway
   **bloquea los puertos SMTP de salida** (25/465/587), así que Gmail/SMTP NO funciona;
   se envía por la **API HTTP de Resend** (puerto 443). Variables en Railway:
   `EMAIL_BACKEND=apps.ingest.resend_email.ResendEmailBackend`,
   `RESEND_API_KEY=<key de resend.com>`,
   `DEFAULT_FROM_EMAIL=SGIS-UCV <onboarding@resend.dev>`.
   `SOAR_ALERT_EMAIL` ya viene a `leopb77@gmail.com`. Resend free sin dominio propio
   solo envía a la dirección con la que te registraste.
5. La **`INGEST_API_KEY`** del entorno a la mano (el launcher trae la de dev por defecto).

## Plan B (a prueba de firewall del salón)

Si la red del salón bloquea las conexiones entrantes (pasó en el 1er avance), el sensor
reproduce el ataque pregrabado y dispara igual las 3 reglas + contención:

```bash
python tools/sensor.py --replay --target https://backend-production-7cfc1.up.railway.app
```
