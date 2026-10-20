"""Einstellungen für Veedelsräume.

Alle betriebsrelevanten Werte kommen aus Umgebungsvariablen (siehe .env.example).
"""

import os
from pathlib import Path
from urllib.parse import unquote, urlparse

BASE_DIR = Path(__file__).resolve().parent.parent


def env(name, default=None):
    return os.environ.get(name, default)


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "ja", "on"}


def env_list(name, default=""):
    return [v.strip() for v in os.environ.get(name, default).split(",") if v.strip()]


DEBUG = env_bool("DJANGO_DEBUG", False)
SECRET_KEY = env("DJANGO_SECRET_KEY") or ("dev-only-insecure-key" if DEBUG else None)
if not SECRET_KEY:
    raise RuntimeError("DJANGO_SECRET_KEY muss gesetzt sein (siehe .env.example).")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

# Öffentliche Basis-URL für Links in E-Mails, z. B. https://veedelsraeume.de
SITE_URL = env("SITE_URL", "http://localhost:8000").rstrip("/")
SITE_NAME = env("SITE_NAME", "Veedelsräume")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "venues",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "config.middleware.SecurityHeadersMiddleware",
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
                "config.context_processors.site",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


def database_from_url(url):
    parsed = urlparse(url)
    if parsed.scheme in {"postgres", "postgresql"}:
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": parsed.path.lstrip("/"),
            "USER": unquote(parsed.username or ""),
            "PASSWORD": unquote(parsed.password or ""),
            "HOST": parsed.hostname or "",
            "PORT": str(parsed.port or ""),
            "CONN_MAX_AGE": 60,
        }
    if parsed.scheme == "sqlite":
        return {"ENGINE": "django.db.backends.sqlite3", "NAME": parsed.path or ":memory:"}
    raise RuntimeError(f"Nicht unterstützte DATABASE_URL: {parsed.scheme}")


DATABASES = {
    "default": database_from_url(env("DATABASE_URL", f"sqlite:///{BASE_DIR / 'db.sqlite3'}"))
}

AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "venues:search"
LOGOUT_REDIRECT_URL = "pages:home"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
# Gültigkeit von Bestätigungs- und Passwort-Links
PASSWORD_RESET_TIMEOUT = 60 * 60 * 48

LANGUAGE_CODE = "de-de"
TIME_ZONE = "Europe/Berlin"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = Path(env("STATIC_ROOT", BASE_DIR / "staticfiles"))
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        if DEBUG
        else "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- E-Mail -----------------------------------------------------------------
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend"
    if DEBUG
    else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = env("EMAIL_HOST", "localhost")
EMAIL_PORT = int(env("EMAIL_PORT", "587"))
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "Veedelsräume <kontakt@example.org>")
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# --- Sitzung und Cookies: nur technisch notwendige Cookies ---------------------
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# --- Sicherheit im Produktivbetrieb ------------------------------------------
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(env("SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# Steht die App hinter einem Reverse Proxy (Caddy), kommt die Client-IP aus
# X-Forwarded-For. Sie wird nie gespeichert, nur gehasht für das Rate-Limit.
TRUST_X_FORWARDED_FOR = env_bool("TRUST_X_FORWARDED_FOR", False)

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "cache_table",
    }
}

# Kartenkacheln: werden erst nach Klick geladen (Zwei-Klick-Lösung).
MAP_TILE_URL = env("MAP_TILE_URL", "https://tile.openstreetmap.org/{z}/{x}/{y}.png")
MAP_TILE_ORIGIN = env("MAP_TILE_ORIGIN", "https://tile.openstreetmap.org")
MAP_ATTRIBUTION = env(
    "MAP_ATTRIBUTION",
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>-Mitwirkende',
)

# --- Fachliche Einstellungen ------------------------------------------------
# Müssen Gruppen nach der E-Mail-Bestätigung zusätzlich von der Redaktion freigeschaltet werden?
GROUP_MANUAL_APPROVAL = env_bool("GROUP_MANUAL_APPROVAL", False)

# Löschfristen in Tagen (siehe docs/DATENSCHUTZ.md)
RETENTION = {
    "unverified_accounts": int(env("RETENTION_UNVERIFIED_ACCOUNTS_DAYS", "7")),
    "unconfirmed_submissions": int(env("RETENTION_UNCONFIRMED_SUBMISSIONS_DAYS", "14")),
    "listing_request_validity": int(env("LISTING_REQUEST_VALIDITY_DAYS", "90")),
    "inactive_accounts": int(env("RETENTION_INACTIVE_ACCOUNTS_DAYS", "730")),
}
# Höchstzahl der Listungsanfragen pro Ort (Erstanfrage + eine Erinnerung)
MAX_LISTING_REQUESTS = int(env("MAX_LISTING_REQUESTS", "2"))

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
    # Keine Request-Logs mit IP-Adressen aus der Anwendung
    "loggers": {"django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False}},
}
