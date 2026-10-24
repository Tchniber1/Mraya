"""Firestore backend (production)."""
from .base import Repository, now_iso


class FirestoreRepository(Repository):
    def __init__(self, client):
        self.db = client

    def _user(self, uid):
        return self.db.collection("users").document(uid)

    def get_user(self, uid):
        snap = self._user(uid).get()
        return snap.to_dict() if snap.exists else None

    def save_user(self, uid, fields):
        ref = self._user(uid)
        payload = dict(fields, updated_at=now_iso())
        if not ref.get().exists:
            payload = {"uid": uid, "xp": 0, "created_at": now_iso(), **payload}
        ref.set(payload, merge=True)
        return ref.get().to_dict()

    def increment_xp(self, uid, amount):
        from google.cloud.firestore import Increment

        ref = self._user(uid)
        ref.set({"uid": uid, "xp": Increment(int(amount))}, merge=True)
        return int(ref.get().to_dict().get("xp", 0))

    def add_analysis(self, uid, analysis, products):
        analysis, products = self._prepare(analysis, products)
        batch = self.db.batch()
        user = self._user(uid)
        batch.set(user.collection("analyses").document(analysis["id"]), analysis)
        for product in products:
            batch.set(user.collection("products").document(product["id"]), product)
        batch.commit()
        return analysis["id"]

    def latest_analysis(self, uid):
        query = (
            self._user(uid)
            .collection("analyses")
            .order_by("created_at", direction="DESCENDING")
            .limit(1)
        )
        docs = list(query.stream())
        return docs[0].to_dict() if docs else None

    def list_products(self, uid):
        # Sorted in Python to avoid needing a composite Firestore index.
        items = [doc.to_dict() for doc in self._user(uid).collection("products").stream()]
        return sorted(items, key=lambda p: (p["created_at"], -p.get("order", 0)), reverse=True)

    def get_product(self, uid, product_id):
        snap = self._user(uid).collection("products").document(product_id).get()
        return snap.to_dict() if snap.exists else None

    def update_product(self, uid, product_id, fields):
        ref = self._user(uid).collection("products").document(product_id)
        if not ref.get().exists:
            return None
        ref.update(fields)
        return ref.get().to_dict()
