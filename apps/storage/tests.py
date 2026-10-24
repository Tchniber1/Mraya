import copy
import io
import time

from django.test import SimpleTestCase

from apps.core.testing import MrayaTestCase

from .firestore import FirestoreRepository


class LocalRepositoryTests(MrayaTestCase):
    def test_user_roundtrip_and_xp(self):
        self.assertIsNone(self.repo.get_user("u1"))
        self.repo.save_user("u1", {"email": "a@b.c"})
        self.repo.save_user("u1", {"age": 20})
        self.assertEqual(self.repo.increment_xp("u1", 40), 40)
        self.assertEqual(self.repo.increment_xp("u1", 10), 50)
        user = self.repo.get_user("u1")
        self.assertEqual((user["email"], user["age"], user["xp"]), ("a@b.c", 20, 50))

    def test_analysis_and_products(self):
        products = [{"category": "clothing", "name": "A"}, {"category": "shoes", "name": "B"}]
        analysis_id = self.repo.add_analysis("u1", {"summary": "s"}, products)
        self.assertEqual(self.repo.latest_analysis("u1")["id"], analysis_id)
        listed = self.repo.list_products("u1")
        self.assertEqual([p["name"] for p in listed], ["A", "B"])  # keeps the model's order
        self.assertTrue(all(p["status"] == "suggested" for p in listed))

        pid = listed[0]["id"]
        self.assertEqual(self.repo.update_product("u1", pid, {"status": "started"})["status"], "started")
        self.assertEqual(self.repo.get_product("u1", pid)["status"], "started")
        self.assertIsNone(self.repo.update_product("u1", "missing", {"status": "x"}))
        self.assertIsNone(self.repo.get_product("nobody", pid))

    def test_users_are_isolated(self):
        self.repo.add_analysis("u1", {"summary": "s"}, [{"category": "hair", "name": "Gel"}])
        self.assertEqual(self.repo.list_products("u2"), [])
        self.assertIsNone(self.repo.latest_analysis("u2"))


class FakeSnap:
    def __init__(self, data):
        self._data = data
        self.exists = data is not None

    def to_dict(self):
        return copy.deepcopy(self._data)


class FakeDoc:
    def __init__(self, store, path):
        self.store, self.path = store, path

    def get(self):
        return FakeSnap(self.store.docs.get(self.path))

    def set(self, data, merge=False):
        base = self.store.docs.get(self.path, {}) if merge else {}
        self.store.docs[self.path] = {**base, **copy.deepcopy(data)}

    def update(self, fields):
        self.store.docs[self.path].update(copy.deepcopy(fields))

    def delete(self):
        self.store.docs.pop(self.path, None)

    def collection(self, name):
        return FakeCollection(self.store, f"{self.path}/{name}")


class FakeCollection:
    def __init__(self, store, path, filters=()):
        self.store, self.path, self.filters = store, path, filters

    def document(self, doc_id):
        return FakeDoc(self.store, f"{self.path}/{doc_id}")

    def where(self, field, op, value):
        assert op == "=="
        return FakeCollection(self.store, self.path, (*self.filters, (field, value)))

    def stream(self):
        prefix = self.path + "/"
        for path, data in list(self.store.docs.items()):
            rest = path[len(prefix):]
            if path.startswith(prefix) and "/" not in rest and all(data.get(f) == v for f, v in self.filters):
                yield FakeSnap(data)


class FakeBatch:
    def __init__(self):
        self.ops = []

    def set(self, ref, data):
        self.ops.append(lambda: ref.set(data))

    def delete(self, ref):
        self.ops.append(ref.delete)

    def commit(self):
        for op in self.ops:
            op()


class FakeFirestore:
    def __init__(self):
        self.docs = {}

    def collection(self, name):
        return FakeCollection(self, name)

    def batch(self):
        return FakeBatch()


class AnalysisHistoryContract:
    """Shared by both backends: per-analysis listing and delete."""

    def make_repo(self):
        raise NotImplementedError

    def test_history_and_delete(self):
        repo = self.make_repo()
        a = repo.add_analysis("u1", {"summary": "A", "created_at": "x"},
                              [{"category": "hair", "name": "A1"}, {"category": "hair", "name": "A2"}])
        time.sleep(0.002)
        b = repo.add_analysis("u1", {"summary": "B"}, [{"category": "shoes", "name": "B1"}])
        listed = repo.list_analyses("u1")
        self.assertEqual([x["id"] for x in listed], [b, a])
        self.assertEqual([x["product_count"] for x in listed], [1, 2])
        self.assertEqual({p["name"] for p in repo.list_products("u1", a)}, {"A1", "A2"})
        self.assertEqual(len(repo.list_products("u1")), 3)
        self.assertEqual(repo.get_analysis("u1", a)["summary"], "A")
        self.assertIsNone(repo.get_analysis("u2", a))

        self.assertTrue(repo.delete_analysis("u1", a))
        self.assertIsNone(repo.get_analysis("u1", a))
        self.assertEqual([p["name"] for p in repo.list_products("u1")], ["B1"])
        self.assertFalse(repo.delete_analysis("u1", "nope"))
        self.assertFalse(repo.delete_analysis("u2", b))
        self.assertEqual(repo.latest_analysis("u1")["id"], b)

    def test_legacy_analysis_without_new_fields(self):
        repo = self.make_repo()
        repo.add_analysis("u1", {"summary": "old"}, [{"category": "hair", "name": "Gel"}])
        [legacy] = repo.list_analyses("u1")
        self.assertNotIn("budget", legacy)
        self.assertEqual(legacy["product_count"], 1)


class LocalHistoryTests(AnalysisHistoryContract, MrayaTestCase):
    def make_repo(self):
        return self.repo


class FirestoreHistoryTests(AnalysisHistoryContract, SimpleTestCase):
    def make_repo(self):
        return FirestoreRepository(FakeFirestore())


class SeedDemoTests(MrayaTestCase):
    def test_seed_demo_offline_has_budget_and_links(self):
        from django.core.management import call_command

        call_command("seed_demo", "--gender", "women", stdout=io.StringIO())
        analysis = self.repo.latest_analysis("demo-user")
        self.assertEqual(analysis["budget"]["currency"], "MAD")
        self.assertLessEqual(analysis["budget"]["used"], analysis["budget"]["limit"])
        products = self.repo.list_products("demo-user", analysis["id"])
        self.assertTrue(products and all(p["link"] for p in products))
