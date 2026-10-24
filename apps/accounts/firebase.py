"""Thin wrapper around firebase-admin (initialised lazily, once)."""
import threading

from django.conf import settings

_lock = threading.Lock()
_app = None


class FirebaseNotConfigured(RuntimeError):
    pass


def _get_app():
    global _app
    with _lock:
        if _app is None:
            import firebase_admin
            from firebase_admin import credentials

            if settings.FIREBASE_CREDENTIALS:
                cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS)
                _app = firebase_admin.initialize_app(cred)
            elif settings.FIREBASE_WEB_CONFIG.get("projectId"):
                # Token verification only needs the project id.
                _app = firebase_admin.initialize_app(
                    options={"projectId": settings.FIREBASE_WEB_CONFIG["projectId"]}
                )
            else:
                raise FirebaseNotConfigured("Set FIREBASE_* variables in .env")
        return _app


def verify_id_token(id_token):
    """Verify a Firebase ID token and return its decoded claims (raises on failure)."""
    from firebase_admin import auth

    return auth.verify_id_token(id_token, app=_get_app(), clock_skew_seconds=10)


def firestore_client():
    from firebase_admin import firestore

    return firestore.client(app=_get_app())
