# Herramientas del mini-SIEM (V1.1)

El bucle completo de la demo:

```
atacante → (TCP) → sensor → (HTTP + X-API-Key) → /api/ingest/events/
                                                        │
                                          motor de reglas (3 reglas)
                                                        │
                                            Incidente automático
                                                        │
                                    Centro de Operaciones (en vivo)
```

Todo es biblioteca estándar: **no hay que instalar nada**.

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
