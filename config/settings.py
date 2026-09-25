"""Ospace — marketing site + driver onboarding portal."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-key-change-me")
DEBUG = env_bool("DEBUG", True)
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]
SITE_URL = os.environ.get("SITE_URL", "http://127.0.0.1:8060").rstrip("/")
CSRF_TRUSTED_ORIGINS = sorted({f"https://{h}" for h in ALLOWED_HOSTS if h not in ("localhost", "127.0.0.1")} | ({SITE_URL} if SITE_URL.startswith("https://") else set()))

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "django.contrib.humanize",
    "apps.web",
    "apps.portal",
]

MIDDLEWARE = [
    "django_pulse.PulseMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.web.context_processors.site",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database: SQLite by default, DATABASE_URL (Postgres) in production.
# SQLite file lives OUTSIDE the app directory in production (SQLITE_PATH), because deploy.sh
# mirrors the repo into the app dir with --delete and would otherwise wipe the database.
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": Path(os.environ.get("SQLITE_PATH", BASE_DIR / "db.sqlite3"))}}
if os.environ.get("DATABASE_URL"):
    import dj_database_url

    DATABASES["default"] = dj_database_url.config(conn_max_age=600, ssl_require=not DEBUG)

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "portal:login"
LOGIN_REDIRECT_URL = "portal:dashboard"
LOGOUT_REDIRECT_URL = "web:home"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Chicago"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        if DEBUG
        else "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", BASE_DIR / "media"))
# Driver uploads live here, outside MEDIA_ROOT, and are only served through permission-checked views.
PRIVATE_ROOT = Path(os.environ.get("PRIVATE_ROOT", BASE_DIR / "private"))
PRIVATE_ROOT.mkdir(parents=True, exist_ok=True)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Uploads: 10 MB per file
MAX_UPLOAD_MB = 10
DATA_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024
ALLOWED_UPLOAD_EXTENSIONS = ["pdf", "jpg", "jpeg", "png", "heic", "webp"]

# Mail
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
if EMAIL_HOST:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
    EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
    EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "Ospace <info@ospacegroup.com>")
SERVER_EMAIL = DEFAULT_FROM_EMAIL
CONTACT_INBOX = os.environ.get("CONTACT_INBOX", "info@ospacegroup.com")

# Business facts shown across the site (single source of truth)
SITE = {
    "name": "Ospace",
    "legal_name": "Ospace LLC",
    "tagline": "Student transportation, driven by people you can trust.",
    "phone": "+1 (346) 666-8739",
    "phone_href": "tel:+13466668739",
    "email": "info@ospacegroup.com",
    "legal_email": "legal@ospacegroup.com",
    "city": "Houston",
    "state": "TX",
    "region": "Houston, Texas",
    "facebook": "https://www.facebook.com/profile.php?id=61578680080626",
    "instagram": "https://www.instagram.com/ospace_llc/",
    "linkedin": "",  # the old site pointed at Wix's own LinkedIn page; add Ospace's when there is one
    "app_ios": "https://apps.apple.com/us/app/adroit-driver/id1512017881",
    "app_android": "https://play.google.com/store/apps/details?id=com.goadroit.adroitpartner",
    "service_number": "149",
}

# Security in production
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", False)
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "SAMEORIGIN"

# Zet8 Pulse
PULSE_APP = "ospace"
PULSE_TOKEN = os.environ.get("PULSE_TOKEN", "")
PULSE_SIGNUPS = [
    ("drivers", "portal.DriverProfile", "created_at"),
    ("inquiries", "web.Inquiry", "created_at"),
]

# Sentry
SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
if SENTRY_DSN:
    import sentry_sdk

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=0.05,
        send_default_pii=False,
        environment="dev" if DEBUG else "prod",
    )

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
