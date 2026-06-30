from pathlib import Path
from datetime import timedelta
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config('SECRET_KEY', default='dev-secret-key-change-in-production')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    # Local apps
    'apps.accounts',
    'apps.incidents',
    'apps.action_plans',
    'apps.reports',
    'apps.ingest',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'sgis.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'sgis.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('POSTGRES_DB', default='sgis_db'),
        'USER': config('POSTGRES_USER', default='sgis_user'),
        'PASSWORD': config('POSTGRES_PASSWORD', default='sgis_pass'),
        'HOST': config('POSTGRES_HOST', default='db'),
        'PORT': config('POSTGRES_PORT', default='5432'),
    }
}

AUTH_USER_MODEL = 'accounts.CustomUser'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es-pe'
TIME_ZONE = 'America/Lima'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=config('ACCESS_TOKEN_LIFETIME_MINUTES', default=60, cast=int)),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=config('REFRESH_TOKEN_LIFETIME_DAYS', default=7, cast=int)),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# ── Ingesta de eventos / mini-SIEM (V1.1) ─────────────────────────────
# El sensor autentica con esta clave en la cabecera X-API-Key.
INGEST_API_KEY = config('INGEST_API_KEY', default='dev-sensor-key-change-me')
# IPs en lista negra (coma-separadas). El motor las marca al instante.
# Defaults = rangos TEST-NET (RFC 5737), no enrutables, solo para demo.
INGEST_BLACKLIST = [
    ip.strip() for ip in
    config('INGEST_BLACKLIST', default='203.0.113.66,198.51.100.7').split(',')
    if ip.strip()
]

# ── Email / notificaciones del playbook SOAR ──────────────────────────
# Dev local: backend de consola (imprime el correo en el log, sin envío real).
# Demo (Railway): Railway BLOQUEA los puertos SMTP de salida (25/465/587), así que
#   cualquier backend SMTP da 'Connection timed out'. Por eso enviamos por la API
#   HTTP de Resend (puerto 443):
#     EMAIL_BACKEND=apps.ingest.resend_email.ResendEmailBackend
#     RESEND_API_KEY=<tu key de resend.com>
#     DEFAULT_FROM_EMAIL=SGIS-UCV <onboarding@resend.dev>   (sin dominio propio)
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
# API key de Resend (envío de correo por HTTP, sin SMTP). Vacía = no enviar.
RESEND_API_KEY = config('RESEND_API_KEY', default='')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='SGIS-UCV <no-reply@sgis.local>')
# Destinatario de las alertas automáticas del playbook SOAR.
SOAR_ALERT_EMAIL = config('SOAR_ALERT_EMAIL', default='leopb77@gmail.com')
# Ventana de agrupación de notificaciones (Opción A): el 1er incidente de una
# ráfaga se notifica al instante; los siguientes dentro de estos segundos se
# resumen en el próximo correo, para no inundar al encargado.
SOAR_ALERT_WINDOW_SECONDS = config('SOAR_ALERT_WINDOW_SECONDS', default=300, cast=int)
