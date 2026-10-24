import json

from apps.analysis.parser import normalise
from apps.core.testing import SAMPLE_REPLY, MrayaTestCase


class DashboardTests(MrayaTestCase):
    def setUp(self):
        super().setUp()
        self.uid = self.sign_in()
        analysis, products = normalise(SAMPLE_REPLY, "MAD")
        self.repo.save_user(self.uid, {"display_name": "Taha", "has_analysis": True, "gender": "men"})
        self.repo.add_analysis(self.uid, analysis, products)
        self.product_id = self.repo.list_products(self.uid)[0]["id"]

    def set_status(self, status, product_id=None):
        return self.client.post(
            f"/dashboard/products/{product_id or self.product_id}/status/",
            data=json.dumps({"status": status}), content_type="application/json",
        )

    def test_dashboard_renders_plan(self):
        response = self.client.get("/dashboard/")
        self.assertContains(response, "Taha's style plan")
        self.assertContains(response, 'data-theme="men"')  # theme follows the stored profile
        self.assertContains(response, "Oxford shirt")
        self.assertContains(response, "Perfume")
        self.assertContains(response, "SPF 50")

    def test_dashboard_without_analysis_goes_home(self):
        self.sign_in(uid="fresh")
        self.assertRedirects(self.client.get("/dashboard/"), "/", fetch_redirect_response=False)

    def test_status_change_awards_xp_once(self):
        first = self.set_status("started").json()
        self.assertEqual(first["xp_gained"], 40)
        self.set_status("not_yet")
        again = self.set_status("started").json()
        self.assertEqual(again["xp_gained"], 0)
        self.assertEqual(again["progress"]["xp"], 40)

    def test_status_change_is_reflected_after_cache(self):
        self.client.get("/dashboard/")  # warm the cache
        self.set_status("not_interested")
        self.assertContains(self.client.get("/dashboard/"), 'data-status="not_interested"')

    def test_invalid_status_and_product(self):
        self.assertEqual(self.set_status("bogus").status_code, 400)
        self.assertEqual(self.set_status("started", product_id="nope").status_code, 400)
        response = self.client.post(f"/dashboard/products/{self.product_id}/status/",
                                    data="not json", content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_other_users_cannot_touch_product(self):
        self.sign_in(uid="intruder")
        self.assertEqual(self.set_status("started").status_code, 400)
