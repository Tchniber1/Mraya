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


class DesignSystemTests(MrayaTestCase):
    def test_icon_tag_renders_inline_svg(self):
        from django.template import Context, Template

        html = Template('{% load ui %}{% icon "shirt" 20 "x" %}{% icon "unknown-name" %}').render(Context())
        self.assertEqual(html.count("<svg"), 2)
        self.assertIn('width="20"', html)
        self.assertIn('aria-hidden="true"', html)

    def test_base_has_account_menu_and_design_assets(self):
        self.sign_in()
        content = self.client.get("/").content.decode()
        for needle in ('href="/settings/"', 'href="/dashboard/history/"', 'role="menu"',
                       "css/ui.css", "js/ui.js", 'class="logo"', ">TT<"):
            self.assertIn(needle, content)

    def test_theme_tokens_are_registered_for_smooth_transitions(self):
        from pathlib import Path

        from django.conf import settings

        css = (Path(settings.BASE_DIR) / "static" / "css" / "tokens.css").read_text(encoding="utf-8")
        for token in ("--bg-1", "--bg-2", "--blob-1", "--text", "--accent", "--surface"):
            self.assertIn(f"@property {token} ", css)
        base = (Path(settings.BASE_DIR) / "static" / "css" / "base.css").read_text(encoding="utf-8")
        self.assertIn("prefers-reduced-motion", base)
        self.assertIn("--bg-1 0.8s", base)


class LogoTests(MrayaTestCase):
    def test_tab_icon_is_the_logo(self):
        content = self.client.get("/accounts/login/").content.decode()
        self.assertIn('<link rel="icon" type="image/png" href="/static/img/favicon.png">', content)
        self.assertIn('<link rel="apple-touch-icon" href="/static/img/apple-touch-icon.png">', content)

    def test_logo_partial_shows_the_logo_image(self):
        content = self.client.get("/accounts/login/").content.decode()
        self.assertIn('<img class="logo-mark" src="/static/img/logo.png" alt=""', content)

    def test_logo_files_exist(self):
        from pathlib import Path

        from django.conf import settings
        from PIL import Image

        for name, size in {"logo.png": 256, "favicon.png": 64, "apple-touch-icon.png": 180}.items():
            with Image.open(Path(settings.BASE_DIR) / "static" / "img" / name) as image:
                self.assertEqual(image.size, (size, size), name)
                self.assertEqual(image.getpixel((0, 0))[3], 0, f"{name} corners should be transparent")
