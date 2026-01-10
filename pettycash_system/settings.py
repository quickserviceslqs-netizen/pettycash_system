"""
Django settings for pettycash_system project.
"""

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

# ---------------------------------------------------------------------
# BASE DIR
# ---------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / ".env")

# ---------------------------------------------------------------------
# SECURITY
# ---------------------------------------------------------------------
SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-change-this-in-production-to-a-secure-random-key-with-at-least-50-characters",
)
DEBUG = os.environ.get("DEBUG", "True") == "True"
ALLOWED_HOSTS = os.environ.get(
    "ALLOWED_HOSTS", "localhost,127.0.0.1,.railway.app,.render.com,.onrender.com"
).split(",")

# Site URL for email invitations
SITE_URL = os.environ.get("SITE_URL", "http://localhost:8000")
SITE_NAME = os.environ.get("SITE_NAME", "Petty Cash System")

# CSRF & Security for production
CSRF_TRUSTED_ORIGINS = os.environ.get(
    "CSRF_TRUSTED_ORIGINS",
    "http://localhost:8000,https://localhost:8000,http://127.0.0.1:8000,https://*.onrender.com",
).split(",")

# Security settings (enabled in production)
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 1  # Minimal value for development (effectively disabled)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
X_FRAME_OPTIONS = "DENY"

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    # SECURE_HSTS_INCLUDE_SUBDOMAINS and SECURE_HSTS_PRELOAD remain True for production

# ---------------------------------------------------------------------
# APPLICATIONS
# ---------------------------------------------------------------------
INSTALLED_APPS = [
    # Default Django apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party apps
    "rest_framework",
    "crispy_forms",
    "crispy_bootstrap5",
    "django_filters",
    # Local apps
    "accounts",
    "organization",
    "transactions",
    "treasury",
    "workflow",
    "reports",
    "settings_manager",
    "system_maintenance",
]

# ---------------------------------------------------------------------
# MIDDLEWARE
# ---------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # For static files in production
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "system_maintenance.middleware.MaintenanceModeMiddleware",  # Block access during maintenance
    "pettycash_system.ip_whitelist_middleware.IPWhitelistMiddleware",  # IP whitelist security
    "pettycash_system.device_auth_middleware.DeviceAuthenticationMiddleware",  # Device whitelist enforcement
    "pettycash_system.middleware.CompanyMiddleware",  # Multi-tenancy: Set company context
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "pettycash_system.ip_whitelist_middleware.SecurityLoggingMiddleware",  # Log security events
]

# ---------------------------------------------------------------------
# URL CONFIG
# ---------------------------------------------------------------------
ROOT_URLCONF = "pettycash_system.urls"

# ---------------------------------------------------------------------
# TEMPLATES
# ---------------------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  # global templates
        "APP_DIRS": True,  # automatically look in app templates
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ---------------------------------------------------------------------
# WSGI
# ---------------------------------------------------------------------
WSGI_APPLICATION = "pettycash_system.wsgi.application"

# ---------------------------------------------------------------------
# DATABASE
# ---------------------------------------------------------------------
# Use DATABASE_URL from environment or fallback to Supabase connection string
DATABASES = {
    "default": dj_database_url.config(
        default=os.environ["DATABASE_URL"],
        conn_max_age=0,  # Disable persistent connections to avoid pool exhaustion
        conn_health_checks=True,
    )
}

# ---------------------------------------------------------------------
# AUTHENTICATION
# ---------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

# Redirects
LOGIN_REDIRECT_URL = "/accounts/role-redirect/"  # Role-based landing
LOGOUT_REDIRECT_URL = "/accounts/login/"  # After logout
LOGIN_URL = "/accounts/login/"  # Default login

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]

# ---------------------------------------------------------------------
# PASSWORD VALIDATION
# ---------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------
# INTERNATIONALIZATION
# ---------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Nairobi"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------
# STATIC & MEDIA FILES
# ---------------------------------------------------------------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"  # For collectstatic

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# WhiteNoise for serving static files in production
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ---------------------------------------------------------------------
# DJANGO CRISPY FORMS
# ---------------------------------------------------------------------
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# ---------------------------------------------------------------------
# REST FRAMEWORK (future API)
# ---------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
}

# ---------------------------------------------------------------------
# DEFAULT AUTO FIELD
# ---------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------
# M-PESA DARAJA API SETTINGS
# ---------------------------------------------------------------------
# Get from environment variables in production
import os

MPESA_CONSUMER_KEY = os.environ.get("MPESA_CONSUMER_KEY", "")
MPESA_CONSUMER_SECRET = os.environ.get("MPESA_CONSUMER_SECRET", "")
MPESA_SHORTCODE = os.environ.get("MPESA_SHORTCODE", "")
MPESA_PASSKEY = os.environ.get("MPESA_PASSKEY", "")
MPESA_CALLBACK_URL = os.environ.get(
    "MPESA_CALLBACK_URL",
    "https://pettycash-system.onrender.com/treasury/api/mpesa/callback/",
)

# ---------------------------------------------------------------------
# ADMIN / SUPERUSER SETTINGS (read from environment)
# ---------------------------------------------------------------------
# These are used by the bootstrap script to create or update the site superuser.
ADMIN_USERNAME = os.environ.get(
    "DJANGO_SUPERUSER_USERNAME"
)  # Optional (defaults to ADMIN_EMAIL when used)
ADMIN_EMAIL = os.environ.get("DJANGO_SUPERUSER_EMAIL")
ADMIN_PASSWORD = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
ADMIN_FIRST_NAME = os.environ.get("DJANGO_SUPERUSER_FIRST_NAME", "")
ADMIN_LAST_NAME = os.environ.get("DJANGO_SUPERUSER_LAST_NAME", "")

# When True, Django will refuse to start if there is no superuser and DJANGO_SUPERUSER_EMAIL/DJANGO_SUPERUSER_PASSWORD are not provided.
REQUIRE_SUPERUSER = os.environ.get("REQUIRE_SUPERUSER", "False").lower() in (
    "1",
    "true",
    "yes",
)

# Enforce requirement at startup to fail early in production if configured
if REQUIRE_SUPERUSER:
    from django.core.exceptions import ImproperlyConfigured

    if not (ADMIN_EMAIL and ADMIN_PASSWORD):
        raise ImproperlyConfigured(
            "REQUIRE_SUPERUSER is set but DJANGO_SUPERUSER_EMAIL/DJANGO_SUPERUSER_PASSWORD are not provided in the environment."
        )

# ---------------------------------------------------------------------
# EMAIL CONFIGURATION
# ---------------------------------------------------------------------
# Email backend settings - can be overridden by environment variables or database settings
def get_email_setting(key, default):
    """Get email setting from database if available, otherwise from environment or default"""
    try:
        from settings_manager.models import SystemSetting
        setting = SystemSetting.objects.filter(key=key, is_active=True).first()
        if setting:
            return setting.get_typed_value()
    except:
        pass
    return os.environ.get(key, default)

EMAIL_BACKEND = get_email_setting(
    "EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_HOST = get_email_setting("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = get_email_setting("EMAIL_PORT", 587)
EMAIL_USE_TLS = get_email_setting("EMAIL_USE_TLS", True)
EMAIL_USE_SSL = get_email_setting("EMAIL_USE_SSL", False)
EMAIL_HOST_USER = get_email_setting("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = get_email_setting("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = get_email_setting("DEFAULT_FROM_EMAIL", "noreply@pettycash.local")

# Email timeout settings
EMAIL_TIMEOUT = get_email_setting("EMAIL_TIMEOUT", 30)
