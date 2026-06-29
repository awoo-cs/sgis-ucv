#!/usr/bin/env python3
"""
Sensor SGIS — V1.1 mini-SIEM.

Es un "honeypot" minúsculo: abre unos puertos, escucha quién se conecta y reporta
cada intento al backend. El motor de reglas del backend decide si eso es un ataque.

    atacante → (TCP) → ESTE sensor → (HTTP + X-API-Key) → /api/ingest/events/

Solo biblioteca estándar (socket, selectors, urllib). Sin pip install, multi-OS.

Modos:
  listen  (por defecto)  abre los puertos y reporta conexiones/logins reales
  replay  (--replay)     reproduce un ataque pregrabado (demo garantizada sin red)

Ejemplos:
  python sensor.py --target http://localhost:8000
  python sensor.py --target https://backend-production-7cfc1.up.railway.app
  python sensor.py --replay          # demo enlatada contra --target
"""
import argparse
import json
import os
import selectors
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

# Puertos no privilegiados (no requieren root) que el sensor finge ofrecer.
# El atacante escanea esta misma lista. La etiqueta es solo cosmética para el log.
SERVICES = {
    2121: 'ftp', 2222: 'ssh', 8080: 'http', 8443: 'https', 3306: 'mysql',
    3389: 'rdp', 5432: 'postgres', 9000: 'php-fpm', 1433: 'mssql',
    5900: 'vnc', 6379: 'redis', 9200: 'elastic',
}
DEFAULT_PORTS = ','.join(str(p) for p in SERVICES)

# ── Colores (ANSI). En Windows 10+ hay que habilitar el modo VT en la consola. ──
if os.name == 'nt':
    try:
        # SetConsoleMode(STDOUT, ENABLE_VIRTUAL_TERMINAL_PROCESSING|...). Sin shell.
        import ctypes
        _k = ctypes.windll.kernel32
        _k.SetConsoleMode(_k.GetStdHandle(-11), 7)
    except Exception:
        pass  # consola antigua: simplemente no habrá color
C = {'red': '\033[31m', 'yel': '\033[33m', 'dim': '\033[2m', 'bold': '\033[1m', 'off': '\033[0m'}


def log(msg, color=None):
    print(f"{C.get(color, '')}{msg}{C['off']}", flush=True)


def post_event(endpoint, api_key, event):
    """Envía un evento al backend. Devuelve la respuesta (dict) o None si falla."""
    body = json.dumps(event).encode()
    req = urllib.request.Request(
        endpoint, data=body, method='POST',
        headers={'Content-Type': 'application/json', 'X-API-Key': api_key},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        log(f"  ! backend respondió {e.code}: {e.read().decode()[:120]}", 'red')
    except Exception as e:
        log(f"  ! no se pudo enviar el evento: {e}", 'red')
    return None


def fetch_blocklist(base_url, api_key):
    """Consulta al backend qué IPs están en contención. Devuelve un set (vacío si falla)."""
    req = urllib.request.Request(
        base_url.rstrip('/') + '/api/ingest/blocklist/',
        headers={'X-API-Key': api_key},
    )
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            return set(json.loads(resp.read()).get('blocked_ips', []))
    except Exception:
        return set()  # si la lectura falla, no contenemos a nadie de más


def diff_blocklist(desired, current):
    """Reconcile declarativo: dado lo que el backend QUIERE bloqueado (`desired`) y
    lo que el sensor TIENE bloqueado ahora (`current`), devuelve (a_agregar, a_quitar).

    Es la misma idea de un firewall real: no se reaplica todo cada vez, solo el delta.
    """
    return desired - current, current - desired


def _selftest():
    """Prueba de la lógica pura del reconcile (sin red ni Windows). `--selftest`."""
    assert diff_blocklist({'a', 'b'}, set()) == ({'a', 'b'}, set())
    assert diff_blocklist({'a'}, {'a', 'b'}) == (set(), {'b'})
    assert diff_blocklist({'a'}, {'a'}) == (set(), set())
    assert diff_blocklist(set(), {'a'}) == (set(), {'a'})
    log("selftest OK", 'yel')


def _is_windows_admin():
    """True solo si corremos en Windows con privilegios de administrador."""
    if os.name != 'nt':
        return False
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _fw_add(ip):
    """Crea una regla de Windows Firewall que bloquea TODO el tráfico entrante de `ip`."""
    subprocess.run(
        ['netsh', 'advfirewall', 'firewall', 'add', 'rule',
         f'name=SGIS-block-{ip}', 'dir=in', 'action=block', f'remoteip={ip}'],
        capture_output=True,
    )


def _fw_del(ip):
    """Borra la regla de firewall de `ip` (idempotente: si no existe, netsh no falla feo)."""
    subprocess.run(
        ['netsh', 'advfirewall', 'firewall', 'delete', 'rule', f'name=SGIS-block-{ip}'],
        capture_output=True,
    )


def report(endpoint, api_key, event):
    """Postea el evento y narra en consola lo que el backend detectó."""
    label = SERVICES.get(event.get('dest_port'), event.get('dest_port') or '-')
    line = f"{event['source_ip']:>15} → {label:<9} [{event['event_type']}]"
    if event.get('username'):
        line += f" user={event['username']}"
    resp = post_event(endpoint, api_key, event)
    det = (resp or {}).get('detection')
    if det:
        flag = 'NUEVO INCIDENTE' if det.get('incident_created') else 'incidente existente'
        log(f"{line}  ⚑ {det['rule'].upper()} → {flag} #{det['incident_id']}", 'red')
    else:
        log(line, 'dim')


# ── Modo LISTEN ───────────────────────────────────────────────────────
def run_listen(endpoint, base_url, api_key, name, ports, auth_port, bind, use_firewall=False):
    sel = selectors.DefaultSelector()
    opened = []
    for port in ports:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((bind, port))
            s.listen(16)
            s.setblocking(False)
            sel.register(s, selectors.EVENT_READ, port)
            opened.append(port)
        except OSError as e:
            log(f"  · no pude abrir el puerto {port} ({e.strerror}), lo salto", 'yel')

    if not opened:
        sys.exit("No se pudo abrir ningún puerto. ¿Otro proceso los ocupa?")

    # ¿Aplicamos firewall REAL? Solo si se pidió Y tenemos privilegios de admin en Windows.
    fw_on = use_firewall and _is_windows_admin()
    if use_firewall and not fw_on:
        log("  · firewall real no disponible (sin admin / no es Windows) → corto solo en la app", 'yel')
    elif fw_on:
        log("  · firewall REAL activo: las IPs contenidas se bloquean con reglas netsh", 'red')

    log(f"\n{C['bold']}Sensor «{name}» escuchando{C['off']} en {bind} puertos: "
        f"{', '.join(map(str, opened))}", 'yel')
    log(f"Reportando a {endpoint}\nEsperando tráfico…  (Ctrl-C para salir)\n")

    blocked = set()                       # lo que ESTE sensor tiene contenido ahora
    last_refresh = time.monotonic() - 3   # negativo → fuerza un primer refresco inmediato

    try:
        while True:
            # Cada 2s preguntamos al backend qué IPs quiere contenidas y reconciliamos
            # solo el delta (igual que un firewall real): aplicamos las nuevas y
            # levantamos las que el operador liberó desde el Centro de Operaciones.
            if time.monotonic() - last_refresh > 2:
                desired = fetch_blocklist(base_url, api_key)
                to_add, to_remove = diff_blocklist(desired, blocked)
                if fw_on:
                    for ip in to_add:
                        _fw_add(ip)
                    for ip in to_remove:
                        _fw_del(ip)
                for ip in to_add:
                    log(f"{ip:>15} ⛔ contención aplicada{' (firewall real)' if fw_on else ''}", 'red')
                for ip in to_remove:
                    log(f"{ip:>15} ✔ contención levantada", 'yel')
                blocked = desired
                last_refresh = time.monotonic()

            for key, _ in sel.select(timeout=1):
                listener, port = key.fileobj, key.data
                try:
                    conn, addr = listener.accept()
                except OSError:
                    continue
                src_ip = addr[0]

                # ── Contención (V1.2 SOAR): IP bloqueada → cortar y no procesar ──
                if src_ip in blocked:
                    conn.close()  # RST: el atacante ve su conexión caer en vivo
                    log(f"{src_ip:>15} → {SERVICES.get(port, port)!s:<9} ⛔ CONTENIDO "
                        f"(IP bloqueada por el SOAR)", 'red')
                    continue

                conn.settimeout(0.4)
                try:
                    data = conn.recv(256)
                except Exception:
                    data = b''
                finally:
                    conn.close()

                event = {'source_ip': src_ip, 'dest_port': port, 'sensor': name, 'raw': {}}
                if port == auth_port and data:
                    # Datos en el puerto de login = intento de autenticación.
                    text = data.decode('latin-1', 'replace').strip()
                    user = text.split(':', 1)[0].split()[0][:60] if text else 'desconocido'
                    event.update(event_type='auth_failure', username=user,
                                 detail=f'Intento de login: {text[:80]}')
                else:
                    event.update(event_type='connection',
                                 detail=f'Conexión a {SERVICES.get(port, port)}')
                report(endpoint, api_key, event)
    except KeyboardInterrupt:
        log("\nSensor detenido.", 'yel')
    finally:
        if fw_on and blocked:
            # No dejamos reglas huérfanas en el host: limpiamos lo que metió este sensor.
            log(f"Limpiando {len(blocked)} regla(s) de firewall…", 'yel')
            for ip in blocked:
                _fw_del(ip)
        for key in list(sel.get_map().values()):
            key.fileobj.close()


# ── Modo REPLAY ───────────────────────────────────────────────────────
def run_replay(endpoint, api_key, name, path, delay):
    with open(path, encoding='utf-8') as f:
        script = json.load(f)
    log(f"\n{C['bold']}Replay{C['off']} de {len(script)} eventos pregrabados → {endpoint}\n", 'yel')
    for event in script:
        wait = event.pop('wait', delay)
        event.setdefault('sensor', name)
        report(endpoint, api_key, event)
        time.sleep(wait)
    log("\nReplay terminado.", 'yel')


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    p = argparse.ArgumentParser(description='Sensor SGIS (mini-SIEM V1.1)')
    p.add_argument('--target', default='http://localhost:8000',
                   help='URL base del backend (default: http://localhost:8000)')
    p.add_argument('--api-key', default=os.environ.get('INGEST_API_KEY', 'dev-sensor-key-change-me'))
    p.add_argument('--name', default=socket.gethostname(), help='Nombre de este sensor')
    p.add_argument('--ports', default=DEFAULT_PORTS, help='Puertos a escuchar (coma-separados)')
    p.add_argument('--auth-port', type=int, default=2222, help='Puerto tratado como login (default: 2222)')
    p.add_argument('--bind', default='0.0.0.0', help='Interfaz donde escuchar')
    p.add_argument('--replay', nargs='?', const=os.path.join(here, 'events_replay.json'),
                   help='Reproduce un ataque pregrabado en vez de escuchar')
    p.add_argument('--replay-delay', type=float, default=0.4, help='Segundos entre eventos del replay')
    p.add_argument('--firewall', action='store_true',
                   help='Aplica reglas de Windows Firewall REALES (netsh) a las IPs contenidas (requiere admin)')
    p.add_argument('--selftest', action='store_true', help='Corre la prueba de la lógica de reconcile y sale')
    args = p.parse_args()

    if args.selftest:
        _selftest()
        return

    endpoint = args.target.rstrip('/') + '/api/ingest/events/'
    if args.replay:
        run_replay(endpoint, args.api_key, args.name, args.replay, args.replay_delay)
    else:
        ports = [int(x) for x in args.ports.split(',') if x.strip()]
        run_listen(endpoint, args.target, args.api_key, args.name, ports, args.auth_port,
                   args.bind, args.firewall)


if __name__ == '__main__':
    main()
