#!/usr/bin/env python3
"""
Atacante SGIS — gemelo Python del atacante PowerShell.

Genera tráfico hostil REAL contra el sensor: primero un escaneo de puertos
(reconocimiento) y luego una ráfaga de fuerza bruta sobre el puerto de login.
El sensor lo ve, lo reporta, y el motor de reglas levanta los incidentes.

Solo biblioteca estándar. Apunta al host donde corre el sensor:

    python attacker.py --target 192.168.1.50
    python attacker.py --target 127.0.0.1        # mismo equipo
"""
import argparse
import random
import socket
import time

PORTS = [2121, 2222, 8080, 8443, 3306, 3389, 5432, 9000, 1433, 5900, 6379, 9200]
USERS = ['admin', 'root', 'administrator', 'postgres', 'oracle', 'test', 'ucv', 'soporte']


def knock(host, port, payload=None, timeout=0.6):
    """Abre una conexión TCP, opcionalmente envía datos, y cierra. True si conectó."""
    try:
        with socket.create_connection((host, port), timeout=timeout) as s:
            if payload:
                s.sendall(payload)
        return True
    except OSError:
        return False


def port_scan(host, ports, delay):
    print(f"\n[1/2] Escaneo de puertos contra {host} ({len(ports)} puertos)…")
    for port in ports:
        ok = knock(host, port)
        print(f"   {host}:{port:<5} {'abierto' if ok else 'cerrado'}")
        time.sleep(delay)


def brute_force(host, auth_port, attempts, delay):
    print(f"\n[2/2] Fuerza bruta contra {host}:{auth_port} ({attempts} intentos)…")
    for i in range(attempts):
        user = random.choice(USERS)
        passwd = random.choice(['123456', 'password', 'admin', 'qwerty', 'root123'])
        knock(host, auth_port, payload=f"{user}:{passwd}\n".encode())
        print(f"   intento {i + 1:>2}/{attempts}  {user}:{passwd}")
        time.sleep(delay)


def main():
    p = argparse.ArgumentParser(description='Atacante de demo SGIS')
    p.add_argument('--target', default='127.0.0.1', help='Host/IP donde corre el sensor')
    p.add_argument('--ports', default=','.join(map(str, PORTS)), help='Puertos a escanear')
    p.add_argument('--auth-port', type=int, default=2222, help='Puerto de login a forzar')
    p.add_argument('--attempts', type=int, default=8, help='Nº de intentos de fuerza bruta')
    p.add_argument('--delay', type=float, default=0.25, help='Segundos entre cada paso')
    args = p.parse_args()

    ports = [int(x) for x in args.ports.split(',') if x.strip()]
    print(f"=== Atacante apuntando a {args.target} ===")
    port_scan(args.target, ports, args.delay)
    brute_force(args.target, args.auth_port, args.attempts, args.delay)
    print("\nListo. Revisa el Centro de Operaciones del SGIS.")


if __name__ == '__main__':
    main()
