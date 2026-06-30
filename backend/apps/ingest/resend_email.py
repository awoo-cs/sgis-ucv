"""Backend de email que envía por la API HTTP de Resend (puerto 443).

Por qué existe: Railway bloquea la salida por los puertos SMTP (25/465/587), así
que cualquier backend SMTP falla con `TimeoutError: [Errno 110] Connection timed
out`. La API de Resend va por HTTPS (443), que sí está abierto.

Solo usa la biblioteca estándar (urllib). Se activa con:
    EMAIL_BACKEND = apps.ingest.resend_email.ResendEmailBackend
    RESEND_API_KEY = <key de resend.com>
    DEFAULT_FROM_EMAIL = SGIS-UCV <onboarding@resend.dev>
"""
import json
import logging
import urllib.error
import urllib.request

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)

RESEND_ENDPOINT = 'https://api.resend.com/emails'


class ResendEmailBackend(BaseEmailBackend):
    """Manda cada mensaje como un POST a la API de Resend. Devuelve cuántos envió."""

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        api_key = getattr(settings, 'RESEND_API_KEY', '')
        if not api_key:
            if not self.fail_silently:
                raise RuntimeError('RESEND_API_KEY no configurada')
            return 0

        sent = 0
        for message in email_messages:
            payload = {
                'from': message.from_email or settings.DEFAULT_FROM_EMAIL,
                'to': list(message.to),
                'subject': message.subject,
                'text': message.body,
            }
            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                RESEND_ENDPOINT, data=data, method='POST',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    resp.read()
                sent += 1
            except urllib.error.HTTPError as e:
                detail = e.read().decode('utf-8', 'replace')[:300]
                logger.error('Resend devolvió %s: %s', e.code, detail)
                if not self.fail_silently:
                    raise
            except Exception:
                logger.exception('Resend rechazó el envío del correo')
                if not self.fail_silently:
                    raise
        return sent
