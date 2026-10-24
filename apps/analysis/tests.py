import json

from django.test import SimpleTestCase

from apps.core.testing import SAMPLE_REPLY, FakeGemma, image_bytes

from .gemma_client import GemmaUnavailable
from .images import InvalidImage, for_ai, load_image, thumbnail_data_uri
from .parser import AnalysisParseError, extract_json, normalise
from .prompts import build_prompt
from .service import AnalysisFailed, run_analysis

PROFILE = {"gender": "men", "age": 22, "budget": 2000, "currency": "MAD", "city": "Rabat",
           "style_preferences": "minimal", "brand_preferences": "", "suggest_brands": True,
           "interests": ["clothing", "perfume"]}


class ParserTests(SimpleTestCase):
    def test_extract_json_from_fenced_text(self):
        text = "Sure!\n```json\n" + json.dumps({"a": 1}) + "\n```\nEnjoy"
        self.assertEqual(extract_json(text), {"a": 1})

    def test_extract_json_errors(self):
        for bad in ("", "no json here", "{broken", "[1, 2]"):
            with self.assertRaises(AnalysisParseError):
                extract_json(bad)

    def test_normalise_maps_aliases_and_prices(self):
        analysis, products = normalise(SAMPLE_REPLY, "MAD")
        self.assertEqual([p["category"] for p in products], ["clothing", "perfume"])
        self.assertEqual(products[1]["price"], 1200)  # "1,200 MAD" -> thousands separator
        self.assertEqual(products[1]["currency"], "MAD")
        self.assertEqual(analysis["style_score"], 72)
        self.assertEqual(analysis["routine"]["morning"], ["Cleanser", "SPF 50"])

    def test_price_formats(self):
        from .parser import _number

        cases = {"299": 299, "12,5 EUR": 12.5, "1,299.50": 1299.5, "1 200 DH": 1200,
                 "about 80$": 80, "free": None, None: None, 45.678: 45.68}
        for raw, expected in cases.items():
            self.assertEqual(_number(raw), expected, raw)

    def test_normalise_requires_products(self):
        with self.assertRaises(AnalysisParseError):
            normalise({"summary": "x", "categories": []}, "MAD")

    def test_normalise_clamps_score_and_tolerates_junk(self):
        data = {**SAMPLE_REPLY, "style_score": "150", "routine": "Wash face; Moisturise", "style_profile": None}
        analysis, _ = normalise(data, "EUR")
        self.assertEqual(analysis["style_score"], 100)
        self.assertEqual(analysis["routine"]["morning"], [])
        self.assertEqual(analysis["style_profile"]["face_shape"], "")


class PromptTests(SimpleTestCase):
    def test_prompt_contains_profile(self):
        prompt = build_prompt(PROFILE)
        for needle in ("man", "2000 MAD", "Rabat", "clothing, perfume", "minimal"):
            self.assertIn(needle, prompt)
        self.assertNotIn("skincare,", prompt.split("Only cover these categories")[1].split("\n")[0])

    def test_brand_preferences(self):
        prompt = build_prompt({**PROFILE, "brand_preferences": "Nike, Zara", "suggest_brands": False})
        self.assertIn("Prefer these brands when they fit: Nike, Zara.", prompt)
        self.assertNotIn("You may also suggest", prompt)


class ImageTests(SimpleTestCase):
    def test_load_and_resize(self):
        image = load_image(image_bytes((3000, 2000), "PNG"), 10 * 1024 * 1024)
        self.assertEqual(image.mode, "RGB")
        self.assertTrue(for_ai(image).startswith(b"\xff\xd8"))
        self.assertTrue(thumbnail_data_uri(image).startswith("data:image/jpeg;base64,"))

    def test_rejects_bad_files(self):
        with self.assertRaises(InvalidImage):
            load_image(b"", 100)
        with self.assertRaises(InvalidImage):
            load_image(b"not an image at all", 10_000)
        with self.assertRaises(InvalidImage):
            load_image(image_bytes(), 10)  # too large
        with self.assertRaises(InvalidImage):
            load_image(image_bytes(fmt="GIF"), 10_000)


class ServiceTests(SimpleTestCase):
    def test_success_sends_both_images(self):
        fake = FakeGemma([SAMPLE_REPLY])
        analysis, products = run_analysis(PROFILE, b"a", b"b", client=fake)
        self.assertEqual(len(products), 2)
        self.assertEqual(fake.calls[0][1], 2)

    def test_retries_once_on_bad_json(self):
        fake = FakeGemma(["oops not json", SAMPLE_REPLY])
        run_analysis(PROFILE, b"a", b"b", client=fake)
        self.assertEqual(len(fake.calls), 2)
        self.assertIn("previous reply was not valid JSON", fake.calls[1][0])

    def test_gives_up_after_two_bad_replies(self):
        with self.assertRaises(AnalysisFailed):
            run_analysis(PROFILE, b"a", b"b", client=FakeGemma(["bad", "still bad"]))

    def test_api_error_becomes_friendly(self):
        with self.assertRaises(AnalysisFailed):
            run_analysis(PROFILE, b"a", b"b", client=FakeGemma([GemmaUnavailable("boom")]))
