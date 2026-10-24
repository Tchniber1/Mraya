from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile

from apps.analysis.gemma_client import GemmaUnavailable
from apps.core.testing import SAMPLE_REPLY, FakeGemma, MrayaTestCase, image_bytes


def form_data(**overrides):
    data = {
        "gender": "women", "age": "24", "budget": "3000", "currency": "MAD", "city": "Rabat",
        "style_preferences": "elegant", "brand_preferences": "", "suggest_brands": "on",
        "interests": ["clothing", "perfume"],
        "full_body": SimpleUploadedFile("body.jpg", image_bytes(), "image/jpeg"),
        "face": SimpleUploadedFile("face.png", image_bytes(fmt="PNG"), "image/png"),
    }
    data.update(overrides)
    return data


class OnboardingTests(MrayaTestCase):
    def setUp(self):
        super().setUp()
        self.uid = self.sign_in()

    def analyze(self, fake, **overrides):
        with mock.patch("apps.analysis.gemma_client.get_client", return_value=fake):
            return self.client.post("/onboarding/analyze/", form_data(**overrides))

    def test_home_shows_form(self):
        response = self.client.get("/")
        self.assertContains(response, "Who are we styling?")
        self.assertContains(response, 'name="full_body"')

    def test_successful_analysis_saves_everything(self):
        response = self.analyze(FakeGemma([SAMPLE_REPLY]))
        self.assertRedirects(response, "/dashboard/", fetch_redirect_response=False)
        user = self.repo.get_user(self.uid)
        self.assertEqual(user["xp"], 150)  # profile 50 + analysis 100
        self.assertEqual(user["gender"], "women")
        self.assertTrue(user["face_thumb"].startswith("data:image/jpeg"))
        self.assertEqual(len(self.repo.list_products(self.uid)), 2)
        self.assertEqual(response.cookies["mraya_theme"].value, "women")

    def test_second_analysis_only_awards_analysis_xp(self):
        self.analyze(FakeGemma([SAMPLE_REPLY]))
        self.analyze(FakeGemma([SAMPLE_REPLY]))
        self.assertEqual(self.repo.get_user(self.uid)["xp"], 250)
        self.assertEqual(len(self.repo.list_products(self.uid)), 4)

    def test_invalid_form_keeps_values(self):
        response = self.analyze(FakeGemma([]), age="5",
                                face=SimpleUploadedFile("x.jpg", b"garbage", "image/jpeg"))
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "not a readable image", status_code=400)
        self.assertContains(response, 'value="3000"', status_code=400)
        self.assertIsNone(self.repo.latest_analysis(self.uid))

    def test_ai_failure_shows_friendly_error(self):
        response = self.analyze(FakeGemma([GemmaUnavailable("down")]))
        self.assertEqual(response.status_code, 502)
        self.assertContains(response, "unreachable", status_code=502)
        self.assertIsNone(self.repo.get_user(self.uid))

    def test_missing_api_key(self):
        with self.settings(GEMINI_API_KEY=""):
            response = self.client.post("/onboarding/analyze/", form_data())
        self.assertContains(response, "missing Gemini API key", status_code=502)
