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

    def _analyses(self, uid):
        return [doc.to_dict() for doc in self._user(uid).collection("analyses").stream()]

    def latest_analysis(self, uid):
        analyses = self._analyses(uid)
        return max(analyses, key=lambda a: a["created_at"]) if analyses else None

    def list_analyses(self, uid):
        products = [doc.to_dict() for doc in self._user(uid).collection("products").stream()]
        return self._with_counts(self._analyses(uid), products)

    def get_analysis(self, uid, analysis_id):
        snap = self._user(uid).collection("analyses").document(analysis_id).get()
        return snap.to_dict() if snap.exists else None

    def delete_analysis(self, uid, analysis_id):
        user = self._user(uid)
        ref = user.collection("analyses").document(analysis_id)
        if not ref.get().exists:
            return False
        batch = self.db.batch()
        batch.delete(ref)
        for doc in user.collection("products").where("analysis_id", "==", analysis_id).stream():
            batch.delete(user.collection("products").document(doc.to_dict()["id"]))
        batch.commit()
        return True

    def list_products(self, uid, analysis_id=None):
        # Sorted in Python to avoid needing a composite Firestore index.
        products = self._user(uid).collection("products")
        if analysis_id is not None:
            products = products.where("analysis_id", "==", analysis_id)
        items = [doc.to_dict() for doc in products.stream()]
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
