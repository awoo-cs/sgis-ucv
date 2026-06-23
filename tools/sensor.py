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
def run_listen(endpoint, api_key, name, ports, auth_port, bind):
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

    log(f"\n{C['bold']}Sensor «{name}» escuchando{C['off']} en {bind} puertos: "
        f"{', '.join(map(str, opened))}", 'yel')
    log(f"Reportando a {endpoint}\nEsperando tráfico…  (Ctrl-C para salir)\n")

    try:
        while True:
            for key, _ in sel.select(timeout=1):
                listener, port = key.fileobj, key.data
                try:
                    conn, addr = listener.accept()
                except OSError:
                    continue
                src_ip = addr[0]
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
    args = p.parse_args()

    endpoint = args.target.rstrip('/') + '/api/ingest/events/'
    if args.replay:
        run_replay(endpoint, args.api_key, args.name, args.replay, args.replay_delay)
    else:
        ports = [int(x) for x in args.ports.split(',') if x.strip()]
        run_listen(endpoint, args.api_key, args.name, ports, args.auth_port, args.bind)


if __name__ == '__main__':
    main()
