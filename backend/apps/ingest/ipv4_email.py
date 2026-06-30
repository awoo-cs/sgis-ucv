"""Backend de email que fuerza IPv4 al abrir la conexión SMTP.

Por qué existe: en Railway, el contenedor resuelve la dirección IPv6 de
`smtp.gmail.com` pero no tiene ruta de salida por IPv6, así que `smtplib` muere
con `OSError: [Errno 101] Network is unreachable` antes de poder autenticar.

La corrección es resolver el host SMTP solo por IPv4. Lo hacemos parcheando
`socket.getaddrinfo` para forzar la familia `AF_INET` SOLO durante `open()`
(la apertura de la conexión) y restaurándolo siempre después, para no afectar
al resto del proceso.
"""
import socket

from django.core.mail.backends.smtp import EmailBackend as _SMTPBackend


class IPv4EmailBackend(_SMTPBackend):
    """SMTP idéntico al de Django, pero resolviendo el servidor solo por IPv4."""

    def open(self):
        original = socket.getaddrinfo

        def ipv4_only(host, port, family=0, *args, **kwargs):
            # Ignoramos la familia pedida y forzamos IPv4.
            return original(host, port, socket.AF_INET, *args, **kwargs)

        socket.getaddrinfo = ipv4_only
        try:
            return super().open()
        finally:
            socket.getaddrinfo = original
