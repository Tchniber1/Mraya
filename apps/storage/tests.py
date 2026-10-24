from apps.core.testing import MrayaTestCase


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
