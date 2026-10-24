"""Storage entry point: ``get_repository()`` returns the configured backend."""
from functools import lru_cache

from django.conf import settings


@lru_cache(maxsize=1)
def get_repository():
    if settings.MRAYA_STORAGE == "firestore":
        from apps.accounts.firebase import firestore_client

        from .firestore import FirestoreRepository

        return FirestoreRepository(firestore_client())

    from .local import LocalJsonRepository

    return LocalJsonRepository(settings.MRAYA_LOCAL_STORE_PATH)
