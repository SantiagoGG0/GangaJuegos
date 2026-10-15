"""
Django settings for gangajuegos project.
"""

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# en local simplemente no existe el archivo .env y esto no hace nada; en el
# servidor carga las variables de entorno reales (claves, base de datos,
# credenciales de pago) sin que queden escritas en ningún archivo de código.
load_dotenv(BASE_DIR / '.env')

# En local, sin la variable de entorno definida, se usa la misma clave de
# siempre para no romper el flujo de desarrollo. En un entorno de prueba/
# producción real, define GS_SECRET_KEY con un valor propio.
SECRET_KEY = os.environ.get('GS_SECRET_KEY', 'django-insecure-2=k^0^zz($b!)8t-$uf2*8169i)grwc*j9vi67bnzwiui$=btn')

DEBUG = os.environ.get('GS_DEBUG', 'true').lower() == 'true'

# separados por coma, ej: "usuario.pythonanywhere.com,midominio.com"
ALLOWED_HOSTS = [h.strip() for h in os.environ.get('GS_ALLOWED_HOSTS', '*').split(',') if h.strip()]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'apps.accounts',
    'apps.catalog',
    'apps.orders',
    'apps.store',
    'apps.panel',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.store.middleware.VisitTrackingMiddleware',
]

ROOT_URLCONF = 'gangajuegos.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.store.context_processors.global_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'gangajuegos.wsgi.application'


# Database
#
# En local, sin GS_DATABASE_URL definida, se usa SQLite como siempre (cero
# fricción para desarrollo). En producción se define GS_DATABASE_URL con la
# cadena de conexión de PostgreSQL, ej:
#   postgres://usuario:clave@localhost:5432/gamesstation
DATABASE_URL = os.environ.get('GS_DATABASE_URL')
if DATABASE_URL:
    DATABASES = {'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600)}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_USER_MODEL = 'accounts.Usuario'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# Internationalization

LANGUAGE_CODE = 'es-co'

TIME_ZONE = 'America/Bogota'

USE_I18N = True

USE_TZ = True


# Static / media files

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'store:auth'
LOGIN_REDIRECT_URL = 'store:account'
LOGOUT_REDIRECT_URL = 'store:home'

# número de WhatsApp del negocio (mismo de ADMIN_SEED en el prototipo), usado
# para construir enlaces wa.me reales en vez del toast simulado del prototipo.
WHATSAPP_NUMBER = '573000000000'

# dominio público usado para construir las URLs absolutas de retorno/webhook
# que Mercado Pago y PayPal necesitan (ellos redirigen/notifican desde fuera,
# no pueden usar una ruta relativa). En local apunta al propio dev server.
SITE_BASE_URL = os.environ.get('GS_SITE_URL', 'http://127.0.0.1:8001')

# Mercado Pago — credenciales de prueba (sandbox) mientras no se pase a
# producción; nunca se hardcodean, siempre vienen de variables de entorno.
MERCADOPAGO_ACCESS_TOKEN = os.environ.get('MERCADOPAGO_ACCESS_TOKEN', '')
MERCADOPAGO_PUBLIC_KEY = os.environ.get('MERCADOPAGO_PUBLIC_KEY', '')

# PayPal — credenciales sandbox por defecto; GS_PAYPAL_MODE='live' para producción.
PAYPAL_CLIENT_ID = os.environ.get('GS_PAYPAL_CLIENT_ID', '')
PAYPAL_CLIENT_SECRET = os.environ.get('GS_PAYPAL_CLIENT_SECRET', '')
PAYPAL_MODE = os.environ.get('GS_PAYPAL_MODE', 'sandbox')
PAYPAL_API_BASE = 'https://api-m.sandbox.paypal.com' if PAYPAL_MODE != 'live' else 'https://api-m.paypal.com'

# Endurecimiento para HTTPS real detrás de Nginx — solo se activa cuando
# DEBUG=false, así que el servidor de desarrollo local (siempre por HTTP)
# no se ve afectado. CSRF_TRUSTED_ORIGINS es obligatorio en Django moderno
# para que los POST (login, checkout, admin) funcionen detrás de un dominio
# propio por HTTPS.
if not DEBUG:
    SECURE_SSL_REDIRECT = os.environ.get('GS_SECURE_SSL_REDIRECT', 'true').lower() == 'true'
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 7
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    CSRF_TRUSTED_ORIGINS = [
        f'https://{h}' for h in ALLOWED_HOSTS if h and h != '*'
    ]
