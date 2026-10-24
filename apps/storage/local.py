"""JSON-file backend for development and tests (no Firebase needed)."""
import copy
import json
import threading
from pathlib import Path

from .base import Repository, now_iso

_LOCK = threading.RLock()


def _product_sort_key(product):
    return (product["created_at"], -product.get("order", 0))


class LocalJsonRepository(Repository):
    def __init__(self, path):
        self.path = Path(path)

    # -- file helpers -------------------------------------------------------
    def _load(self):
        if not self.path.exists():
            return {"users": {}}
        with self.path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    def _dump(self, data):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        tmp.replace(self.path)

    @staticmethod
    def _bucket(data, uid):
        return data["users"].setdefault(uid, {"doc": None, "analyses": {}, "products": {}})

    @staticmethod
    def _new_doc(uid):
        return {"uid": uid, "xp": 0, "created_at": now_iso()}

    # -- Repository API -----------------------------------------------------
    def get_user(self, uid):
        with _LOCK:
            bucket = self._load()["users"].get(uid)
            return copy.deepcopy(bucket["doc"]) if bucket and bucket["doc"] else None

    def save_user(self, uid, fields):
        with _LOCK:
            data = self._load()
            bucket = self._bucket(data, uid)
            doc = bucket["doc"] or self._new_doc(uid)
            doc.update(fields)
            doc["updated_at"] = now_iso()
            bucket["doc"] = doc
            self._dump(data)
            return copy.deepcopy(doc)

    def increment_xp(self, uid, amount):
        with _LOCK:
            data = self._load()
            bucket = self._bucket(data, uid)
            doc = bucket["doc"] or self._new_doc(uid)
            doc["xp"] = int(doc.get("xp", 0)) + int(amount)
            bucket["doc"] = doc
            self._dump(data)
            return doc["xp"]

    def add_analysis(self, uid, analysis, products):
        analysis, products = self._prepare(analysis, products)
        with _LOCK:
            data = self._load()
            bucket = self._bucket(data, uid)
            bucket["analyses"][analysis["id"]] = analysis
            for product in products:
                bucket["products"][product["id"]] = product
            self._dump(data)
        return analysis["id"]

    def latest_analysis(self, uid):
        with _LOCK:
            bucket = self._load()["users"].get(uid)
            if not bucket or not bucket["analyses"]:
                return None
            latest = max(bucket["analyses"].values(), key=lambda a: a["created_at"])
            return copy.deepcopy(latest)

    def list_products(self, uid):
        with _LOCK:
            bucket = self._load()["users"].get(uid)
            items = list(bucket["products"].values()) if bucket else []
        return copy.deepcopy(sorted(items, key=_product_sort_key, reverse=True))

    def get_product(self, uid, product_id):
        with _LOCK:
            bucket = self._load()["users"].get(uid)
            product = bucket["products"].get(product_id) if bucket else None
            return copy.deepcopy(product)

    def update_product(self, uid, product_id, fields):
        with _LOCK:
            data = self._load()
            bucket = data["users"].get(uid)
            if not bucket or product_id not in bucket["products"]:
                return None
            bucket["products"][product_id].update(fields)
            self._dump(data)
            return copy.deepcopy(bucket["products"][product_id])
