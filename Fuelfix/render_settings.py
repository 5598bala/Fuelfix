"""Render-specific production settings for FuelFix."""

import os

_render_host = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "").strip()
if _render_host:
    _allowed_hosts = [
        host.strip()
        for host in os.environ.get("ALLOWED_HOSTS", "").split(",")
        if host.strip()
    ]
    if _render_host not in _allowed_hosts:
        _allowed_hosts.append(_render_host)
    os.environ["ALLOWED_HOSTS"] = ",".join(_allowed_hosts)

    _csrf_origins = [
        origin.strip()
        for origin in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")
        if origin.strip()
    ]
    _render_origin = f"https://{_render_host}"
    if _render_origin not in _csrf_origins:
        _csrf_origins.append(_render_origin)
    os.environ["CSRF_TRUSTED_ORIGINS"] = ",".join(_csrf_origins)

os.environ.setdefault("DEBUG", "False")

from .settings import *  # noqa: E402,F403

import dj_database_url  # noqa: E402

_database_url = os.environ.get("DATABASE_URL", "").strip()
if not _database_url:
    raise RuntimeError("Render requires DATABASE_URL so FuelFix data persists in PostgreSQL.")

DEBUG = False
DATABASES = {
    "default": dj_database_url.parse(
        _database_url,
        conn_max_age=600,
        conn_health_checks=True,
        ssl_require=True,
    )
}

MIDDLEWARE = list(MIDDLEWARE)
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

if _render_host:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    if _render_host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_render_host)
    if _render_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(_render_origin)

_google_client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
_google_client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
if _google_client_id and _google_client_secret:
    SOCIALACCOUNT_PROVIDERS = {
        **SOCIALACCOUNT_PROVIDERS,
        "google": {
            **SOCIALACCOUNT_PROVIDERS.get("google", {}),
            "APPS": [
                {
                    "client_id": _google_client_id,
                    "secret": _google_client_secret,
                    "key": "",
                }
            ],
        },
    }
