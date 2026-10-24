"""Storage interface shared by every backend.

Data is document-shaped so it maps 1:1 onto Firestore:
    users/{uid}                      -> profile, xp, thumbnails
    users/{uid}/analyses/{id}        -> one Gemma analysis
    users/{uid}/products/{id}        -> one recommended product
"""
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone

PRODUCT_STATUSES = ("suggested", "started", "not_yet", "not_interested")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def new_id():
    return uuid.uuid4().hex[:16]


class Repository(ABC):
    @abstractmethod
    def get_user(self, uid):
        """Return the user document as a dict, or None."""

    @abstractmethod
    def save_user(self, uid, fields):
        """Merge ``fields`` into the user document (creating it if needed). Returns the document."""

    @abstractmethod
    def increment_xp(self, uid, amount):
        """Add ``amount`` XP and return the new total."""

    @abstractmethod
    def add_analysis(self, uid, analysis, products):
        """Store an analysis and its products. Returns the analysis id."""

    @abstractmethod
    def latest_analysis(self, uid):
        """Return the most recent analysis dict, or None."""

    @abstractmethod
    def list_products(self, uid):
        """Return all products, newest first."""

    @abstractmethod
    def get_product(self, uid, product_id):
        """Return one product dict, or None."""

    @abstractmethod
    def update_product(self, uid, product_id, fields):
        """Merge ``fields`` into a product. Returns the updated product, or None if missing."""

    @staticmethod
    def _prepare(analysis, products):
        analysis_id = new_id()
        created = now_iso()
        analysis = {**analysis, "id": analysis_id, "created_at": created}
        prepared = []
        for index, product in enumerate(products):
            prepared.append(
                {
                    **product,
                    "id": new_id(),
                    "analysis_id": analysis_id,
                    "status": "suggested",
                    "xp_events": [],
                    "created_at": created,
                    "order": index,
                }
            )
        return analysis, prepared
