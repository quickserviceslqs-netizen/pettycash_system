"""
Django settings for pettycash_system project.
"""

from pathlib import Path
import os
import dj_database_url

# ---------------------------------------------------------------------
# BASE DIR
# ---------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------
# SECURITY
# ---------------------------------------------------------------------
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-%7!es6s0(ak^5(mmz_uh65^vy6*za^h+9+9ojdotnwe0-&pn%@')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,.railway.app,.render.com,.onrender.com').split(',')

# Site URL for email invitations
SITE_URL = os.environ.get('SITE_URL', 'http://localhost:8000')
SITE_NAME = os.environ.get('SITE_NAME', 'Petty Cash System')

# CSRF & Security for production
CSRF_TRUSTED_ORIGINS = os.environ.get('CSRF_TRUSTED_ORIGINS', 'http://localhost:8000,http://127.0.0.1:8000,https://*.onrender.com').split(',')
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'

# ---------------------------------------------------------------------
# APPLICATIONS
# ---------------------------------------------------------------------
INSTALLED_APPS = [
    # Default Django apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'rest_framework',
    'crispy_forms',
    'crispy_bootstrap5',
    'django_filters',

    # Local apps
    'accounts',
    'organization',
    'transactions',
    'treasury',
    'workflow',
    'reports',
    'settings_manager',
]

# ---------------------------------------------------------------------
# MIDDLEWARE
# ---------------------------------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # For static files in production
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'pettycash_system.ip_whitelist_middleware.IPWhitelistMiddleware',  # IP whitelist security
    'pettycash_system.device_auth_middleware.DeviceAuthenticationMiddleware',  # Device whitelist enforcement
    'pettycash_system.middleware.CompanyMiddleware',  # Multi-tenancy: Set company context
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'pettycash_system.ip_whitelist_middleware.SecurityLoggingMiddleware',  # Log security events
]

# ---------------------------------------------------------------------
# URL CONFIG
# ---------------------------------------------------------------------
ROOT_URLCONF = 'pettycash_system.urls'

# ---------------------------------------------------------------------
# TEMPLATES
# ---------------------------------------------------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],  # global templates
        'APP_DIRS': True,                  # automatically look in app templates
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

# ---------------------------------------------------------------------
# WSGI
# ---------------------------------------------------------------------
WSGI_APPLICATION = 'pettycash_system.wsgi.application'

# ---------------------------------------------------------------------
# DATABASE
# ---------------------------------------------------------------------
# Use DATABASE_URL from environment (Railway/Render) or fallback to local PostgreSQL
DATABASES = {
    'default': dj_database_url.config(
        default=f"postgresql://chelotian:35315619@Ian@localhost:5432/pettycash_db",
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# ---------------------------------------------------------------------
# AUTHENTICATION
# ---------------------------------------------------------------------
AUTH_USER_MODEL = 'accounts.User'

# Redirects
LOGIN_REDIRECT_URL = '/accounts/role-redirect/'  # Role-based landing
LOGOUT_REDIRECT_URL = '/accounts/login/'        # After logout
LOGIN_URL = '/accounts/login/'                  # Default login

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

# ---------------------------------------------------------------------
# PASSWORD VALIDATION
# ---------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ---------------------------------------------------------------------
# INTERNATIONALIZATION
# ---------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------
# STATIC & MEDIA FILES
# ---------------------------------------------------------------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"  # For collectstatic

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / "media"

# WhiteNoise for serving static files in production
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ---------------------------------------------------------------------
# DJANGO CRISPY FORMS
# ---------------------------------------------------------------------
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# ---------------------------------------------------------------------
# REST FRAMEWORK (future API)
# ---------------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
}

# ---------------------------------------------------------------------
# DEFAULT AUTO FIELD
# ---------------------------------------------------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------
# M-PESA DARAJA API SETTINGS
# ---------------------------------------------------------------------
# Get from environment variables in production
import os

MPESA_CONSUMER_KEY = os.environ.get('MPESA_CONSUMER_KEY', '')
MPESA_CONSUMER_SECRET = os.environ.get('MPESA_CONSUMER_SECRET', '')
MPESA_SHORTCODE = os.environ.get('MPESA_SHORTCODE', '')
MPESA_PASSKEY = os.environ.get('MPESA_PASSKEY', '')
MPESA_CALLBACK_URL = os.environ.get('MPESA_CALLBACK_URL', 'https://pettycash-system.onrender.com/treasury/api/mpesa/callback/')

