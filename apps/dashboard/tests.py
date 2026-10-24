import json
import time

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


def product(name, category="clothing", price=100.0, **extra):
    return {"category": category, "name": name, "brand": "B", "price": price, "currency": "MAD",
            "where_to_buy": "", "why": "", **extra}


class TwoAnalysesCase(MrayaTestCase):
    def setUp(self):
        super().setUp()
        self.uid = self.sign_in()
        self.repo.save_user(self.uid, {"display_name": "Taha", "has_analysis": True, "gender": "women", "xp": 150})
        base = {"summary": "s", "style_profile": {}, "routine": {}, "style_score": 60}
        self.old = self.repo.add_analysis(
            self.uid, {**base, "summary": "Old plan", "categories": [{"category": "clothing", "label": "Clothing", "advice": ""}]},
            [product("Old jacket")],
        )
        time.sleep(0.002)
        self.new = self.repo.add_analysis(
            self.uid,
            {**base, "summary": "New plan", "budget": {"limit": 1000, "used": 400, "currency": "MAD", "dropped": 0},
             "categories": [{"category": "clothing", "label": "Clothing", "advice": "Go slim."},
                            {"category": "perfume", "label": "Perfume", "advice": "Fresh notes."},
                            {"category": "shoes", "label": "Shoes", "advice": "Clean sneakers."}]},
            [product("New shirt", image_url="https://img.example/s.jpg", link="https://shop.example/s", store="Zara",
                     price_source="store", origin="local", origin_country="ma"),
             product("Plain tee"),
             product("Paris loafer", category="shoes", image_url="https://img.example/l.jpg",
                     link="https://shop.example/l", store="Galeries", price=300.0, price_converted=True,
                     origin="abroad", origin_country="fr")],
        )



class HistoryTests(TwoAnalysesCase):
    def test_dashboard_shows_only_latest_analysis(self):
        response = self.client.get("/dashboard/")
        self.assertContains(response, "New shirt")
        self.assertNotContains(response, "Old jacket")
        self.assertContains(response, "400 of 1000 MAD used")

    def test_detail_and_access_control(self):
        self.assertContains(self.client.get(f"/dashboard/{self.old}/"), "Old jacket")
        self.sign_in(uid="intruder")
        self.assertEqual(self.client.get(f"/dashboard/{self.old}/").status_code, 404)

    def test_history_lists_newest_first(self):
        content = self.client.get("/dashboard/history/").content.decode()
        self.assertLess(content.index("New plan"), content.index("Old plan"))

    def test_delete_current_then_last(self):
        response = self.client.post(f"/dashboard/{self.new}/delete/")
        self.assertRedirects(response, "/dashboard/", fetch_redirect_response=False)
        self.assertContains(self.client.get("/dashboard/"), "Old jacket")
        response = self.client.post(f"/dashboard/{self.old}/delete/")
        self.assertRedirects(response, "/", fetch_redirect_response=False)
        user = self.repo.get_user(self.uid)
        self.assertFalse(user["has_analysis"])
        self.assertEqual(user["xp"], 150)

    def test_delete_rejects_get_and_unknown(self):
        self.assertEqual(self.client.get(f"/dashboard/{self.new}/delete/").status_code, 405)
        self.assertEqual(self.client.post("/dashboard/nope/delete/").status_code, 404)

    def test_legacy_analysis_renders(self):
        self.assertEqual(self.client.get(f"/dashboard/{self.old}/").status_code, 200)

    def test_product_images_links_and_fallback_icon(self):
        content = self.client.get("/dashboard/").content.decode()
        self.assertIn('src="https://img.example/s.jpg"', content)
        self.assertIn("data-fallback", content)
        self.assertIn('href="https://shop.example/s"', content)
        self.assertIn('rel="noopener noreferrer"', content)
        plain = content[content.index("Plain tee") - 1500:content.index("Plain tee")]
        self.assertIn('class="product-icon"', plain)

    def test_tabs_markup(self):
        content = self.client.get("/dashboard/").content.decode()
        self.assertIn('role="tablist"', content)
        self.assertIn('data-tab="abroad"', content)
        self.assertIn('data-panel="clothing"', content)

    def test_empty_category_message(self):
        self.assertContains(self.client.get("/dashboard/"), "No pick fits your budget")

    def test_local_cards_do_not_show_a_country(self):
        content = self.client.get("/dashboard/").content.decode()
        end = content.index(">New shirt</h3>")
        local_card = content[content.rindex("<article", 0, end):end]
        self.assertNotIn("product-country", local_card)

    def test_abroad_section(self):
        content = self.client.get("/dashboard/").content.decode()
        self.assertIn("available abroad", content.lower())
        self.assertIn("Price may not include shipping or customs.", content)
        self.assertIn("\U0001F1EB\U0001F1F7", content)
        shoes = content.index('id="cat-shoes"') if 'id="cat-shoes"' in content else -1
        abroad = content.lower().index("available abroad")
        self.assertGreater(content.index("Paris loafer"), abroad)
        self.assertEqual(shoes, -1)  # shoes only exist abroad, so no local shoes section


class ExportTests(TwoAnalysesCase):
    def setUp(self):
        super().setUp()
        items = self.repo.list_products(self.uid, self.new)
        by_name = {p["name"]: p["id"] for p in items}
        self.repo.update_product(self.uid, by_name["New shirt"], {"status": "started"})
        self.repo.update_product(self.uid, by_name["Plain tee"], {"status": "not_interested"})

    def test_csv(self):
        response = self.client.get(f"/dashboard/{self.new}/export.csv")
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertRegex(response["Content-Disposition"], r'attachment; filename="mraya-buying-list-\d{4}-\d{2}-\d{2}\.csv"')
        body = response.content.decode("utf-8")
        self.assertTrue(body.startswith("﻿"))
        lines = body.lstrip("﻿").splitlines()
        self.assertEqual(lines[0], "category,brand,name,price,currency,store,link,status")
        self.assertIn("Clothing,B,New shirt,100,MAD,Zara,https://shop.example/s,Bought", lines)
        self.assertTrue(any(line.startswith("Shoes,B,Paris loafer") and line.endswith("To decide") for line in lines))
        self.assertNotIn("Plain tee", body)

    def test_csv_neutralises_formulas(self):
        from .export import export_rows

        rows = export_rows([{"category": "hair", "brand": "+B", "name": "=HYPERLINK(\"http://x\")",
                             "price": 5, "currency": "MAD", "store": "@Shop", "link": "", "status": "suggested"}])
        self.assertEqual(rows[1][1:3], ["'+B", "'=HYPERLINK(\"http://x\")"])
        self.assertEqual(rows[1][5], "'@Shop")

    def test_print_page(self):
        response = self.client.get(f"/dashboard/{self.new}/export/print/")
        self.assertContains(response, "window.print")
        self.assertContains(response, 'href="https://shop.example/s"')
        self.assertContains(response, "400 MAD")  # total of the exported items: 100 + 300
        self.assertNotContains(response, "Plain tee")

    def test_export_access_control(self):
        self.sign_in(uid="intruder")
        self.assertEqual(self.client.get(f"/dashboard/{self.new}/export.csv").status_code, 404)
        self.assertEqual(self.client.get(f"/dashboard/{self.new}/export/print/").status_code, 404)
