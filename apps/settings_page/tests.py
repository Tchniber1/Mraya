import base64
import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from PIL import Image

from apps.core.testing import MrayaTestCase, image_bytes


class SettingsPageTests(MrayaTestCase):
    def setUp(self):
        super().setUp()
        self.uid = self.sign_in()
        self.repo.save_user(self.uid, {"display_name": "Taha Test", "gender": "men", "currency": "MAD",
                                       "country": "ma", "google_picture": "https://lh3.example/me.jpg"})

    def upload(self, data, name="me.png", content_type="image/png"):
        return self.client.post("/settings/", {"action": "upload_avatar",
                                               "avatar": SimpleUploadedFile(name, data, content_type)})

    def test_requires_login(self):
        self.assertRedirects(Client().get("/settings/"), "/accounts/login/", fetch_redirect_response=False)

    def test_page_shows_google_picture_by_default(self):
        response = self.client.get("/settings/")
        self.assertContains(response, 'src="https://lh3.example/me.jpg"', count=2)  # header + settings card

    def test_upload_avatar(self):
        response = self.upload(image_bytes((300, 100), "PNG"))
        self.assertRedirects(response, "/settings/", fetch_redirect_response=False)
        avatar = self.repo.get_user(self.uid)["avatar"]
        self.assertTrue(avatar.startswith("data:image/jpeg;base64,"))
        self.assertContains(self.client.get("/settings/"), avatar[:60])

    def test_avatar_change_shows_on_cached_dashboard(self):
        self.repo.add_analysis(self.uid, {"summary": "s", "categories": []}, [{"category": "hair", "name": "Gel"}])
        self.repo.save_user(self.uid, {"has_analysis": True})
        self.client.get("/dashboard/")  # warm the dashboard cache
        self.upload(image_bytes((300, 300), "PNG"))
        avatar = self.repo.get_user(self.uid)["avatar"]
        self.assertContains(self.client.get("/dashboard/"), avatar[:60])
        self.client.post("/settings/", {"action": "remove_avatar"})
        self.assertNotContains(self.client.get("/dashboard/"), avatar[:60])

    def test_upload_rejects_bad_files(self):
        response = self.upload(b"definitely not an image", "x.txt", "text/plain")
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "not a readable image", status_code=400)
        with override_settings(MRAYA_MAX_IMAGE_BYTES=10):
            self.assertEqual(self.upload(image_bytes()).status_code, 400)
        self.assertNotIn("avatar", self.repo.get_user(self.uid))

    def test_remove_avatar_falls_back_to_google_then_initials(self):
        self.upload(image_bytes((300, 300), "PNG"))
        self.client.post("/settings/", {"action": "remove_avatar"})
        self.assertEqual(self.repo.get_user(self.uid).get("avatar", ""), "")
        self.assertContains(self.client.get("/settings/"), "https://lh3.example/me.jpg")
        self.repo.save_user(self.uid, {"google_picture": ""})
        self.assertContains(self.client.get("/settings/"), ">TT<")

    def test_save_profile(self):
        response = self.client.post("/settings/", {"action": "save", "display_name": "Taha C",
                                                   "gender": "women", "country": "fr", "currency": "EUR"})
        self.assertRedirects(response, "/settings/", fetch_redirect_response=False)
        user = self.repo.get_user(self.uid)
        self.assertEqual((user["display_name"], user["gender"], user["country"], user["currency"]),
                         ("Taha C", "women", "fr", "EUR"))
        self.assertEqual(response.cookies["mraya_theme"].value, "women")

    def test_save_rejects_bad_values(self):
        response = self.client.post("/settings/", {"action": "save", "display_name": "x",
                                                   "gender": "robot", "country": "ma", "currency": "MAD"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.repo.get_user(self.uid)["gender"], "men")


class AvatarImageTests(MrayaTestCase):
    def test_avatar_is_square_256(self):
        from apps.analysis.images import avatar_data_uri, load_image

        uri = avatar_data_uri(load_image(image_bytes((300, 100), "PNG"), 10_000_000))
        image = Image.open(io.BytesIO(base64.b64decode(uri.split(",", 1)[1])))
        self.assertEqual(image.size, (256, 256))
        self.assertEqual(image.format, "JPEG")
