"""Django settings for Mraya.

All secrets come from environment variables (see .env.example).
"""
import os
from pathlib import Path

from dotenv import load_dotenv

from config.plugins import discover_plugins

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-insecure-change-me")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]

MRAYA_APPS = [
    "apps.core",
    "apps.accounts",
    "apps.storage",
    "apps.analysis",
    "apps.onboarding",
    "apps.progress",
    "apps.dashboard",
    "apps.settings_page",
]

# Update packages ("mraya.plugins" entry points or MRAYA_PLUGINS env var)
MRAYA_PLUGIN_APPS = discover_plugins(os.getenv("MRAYA_PLUGINS", ""))

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    *MRAYA_APPS,
    *MRAYA_PLUGIN_APPS,
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
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
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.mraya",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Only used by Django internals/tests; user data lives in Firestore or the local JSON store.
DATABASES = {
    "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"},
}

# --- Sessions & cookies: remember the user for 30 days ---
SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
# Google sign-in popups must be able to post the credential back to this page.
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin-allow-popups"
MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"
THEME_COOKIE_NAME = "mraya_theme"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "mraya",
        "TIMEOUT": 300,
    }
}

# --- Uploads ---
DATA_UPLOAD_MAX_MEMORY_SIZE = 25 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 25 * 1024 * 1024
MRAYA_MAX_IMAGE_BYTES = 10 * 1024 * 1024

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Casablanca"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Gemma 4 via the Gemini API ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMMA_MODEL = os.getenv("GEMMA_MODEL", "gemma-4-31b-it")
GEMMA_TIMEOUT_MS = int(os.getenv("GEMMA_TIMEOUT_MS", "180000"))

# Real product images, links and prices (https://serper.dev). Optional.
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "").strip()
SERPER_COUNTRY = os.getenv("SERPER_COUNTRY", "ma").strip().lower() or "ma"

# --- Firebase ---
FIREBASE_WEB_CONFIG = {
    "apiKey": os.getenv("FIREBASE_API_KEY", ""),
    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN", ""),
    "projectId": os.getenv("FIREBASE_PROJECT_ID", ""),
    "appId": os.getenv("FIREBASE_APP_ID", ""),
}
FIREBASE_AUTH_ENABLED = all(FIREBASE_WEB_CONFIG.values())
# Optional: sign in with Google Identity Services instead of the Firebase popup
# (for networks that block *.firebaseapp.com). Use the project's "Web client" OAuth id.
GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "").strip()
_cred = os.getenv("FIREBASE_CREDENTIALS", "")
FIREBASE_CREDENTIALS = str(BASE_DIR / _cred) if _cred and not os.path.isabs(_cred) else _cred
_has_cred_file = bool(FIREBASE_CREDENTIALS) and os.path.isfile(FIREBASE_CREDENTIALS)

MRAYA_STORAGE = os.getenv("MRAYA_STORAGE", "").strip() or ("firestore" if _has_cred_file else "local")
MRAYA_LOCAL_STORE_PATH = BASE_DIR / "data" / "local_store.json"
MRAYA_DEV_LOGIN = DEBUG and env_bool("MRAYA_DEV_LOGIN", True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {"apps": {"handlers": ["console"], "level": "INFO"}},
}
