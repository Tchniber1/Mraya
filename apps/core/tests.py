from django.test import SimpleTestCase

from apps.core.testing import MrayaTestCase
from config.plugins import discover_plugins


class ThemeTests(MrayaTestCase):
    def test_default_theme_is_neutral(self):
        self.assertContains(self.client.get("/accounts/login/"), 'data-theme="neutral"')

    def test_set_theme_cookie(self):
        response = self.client.post("/theme/", {"theme": "men"})
        self.assertEqual(response.cookies["mraya_theme"].value, "men")
        self.assertContains(self.client.get("/accounts/login/"), 'data-theme="men"')

    def test_set_theme_rejects_unknown(self):
        self.assertEqual(self.client.post("/theme/", {"theme": "purple"}).status_code, 400)

    def test_signed_in_theme_follows_session(self):
        self.sign_in()
        self.client.post("/theme/", {"theme": "women"})
        self.client.cookies.pop("mraya_theme")
        self.assertContains(self.client.get("/"), 'data-theme="women"')


class PluginTests(SimpleTestCase):
    def test_unknown_plugins_are_skipped(self):
        self.assertEqual(discover_plugins("definitely_not_a_module_xyz"), [])

    def test_importable_plugin_is_kept(self):
        self.assertEqual(discover_plugins("json, json"), ["json"])
