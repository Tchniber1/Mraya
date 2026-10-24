import json
from pathlib import Path

from django.test import SimpleTestCase, override_settings

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

    def test_normalise_adds_search_query_and_priority(self):
        _, products = normalise(SAMPLE_REPLY, "MAD")
        self.assertEqual(products[0]["search_query"], "Zara Oxford shirt")
        self.assertEqual(products[0]["priority"], "nice")
        reply = json.loads(json.dumps(SAMPLE_REPLY))
        reply["categories"][0]["products"][0]["priority"] = "ESSENTIAL"
        reply["categories"][1]["products"][0]["priority"] = "maybe"
        _, products = normalise(reply, "MAD")
        self.assertEqual([x["priority"] for x in products], ["essential", "nice"])

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

    def test_prompt_contains_category_budgets(self):
        prompt = build_prompt(PROFILE)
        self.assertIn("clothing: up to 1400 MAD", prompt)
        self.assertIn("perfume: up to 600 MAD", prompt)
        self.assertIn("search_query", prompt)


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


@override_settings(SERPER_API_KEY="")
class ServiceTests(SimpleTestCase):
    def test_budget_is_enforced(self):
        analysis, products = run_analysis({**PROFILE, "budget": 1000}, b"a", b"b",
                                          client=FakeGemma([SAMPLE_REPLY]), fetch=FakeFetch())
        self.assertEqual([p["name"] for p in products], ["Oxford shirt"])
        self.assertEqual(analysis["budget"], {"limit": 1000, "used": 299, "currency": "MAD", "dropped": 1})

    def test_products_are_enriched(self):
        _, products = run_analysis(PROFILE, b"a", b"b", client=FakeGemma([SAMPLE_REPLY]),
                                   fetch=FakeFetch({"ma": FIXTURE}))
        self.assertTrue(all(p["link"] for p in products))
        self.assertEqual(products[0]["store"], "SweetCare")

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


class CurrencyTests(SimpleTestCase):
    def test_parse_price_formats(self):
        from .currency import parse_price

        cases = {"MAD\xa094.09": (94.09, "MAD"), "€7.49": (7.49, "EUR"), "1 299,00 MAD": (1299.0, "MAD"),
                 "CA$30": (30.0, "CAD"),
                 "$12.99/month": (12.99, "USD"), "£20": (20.0, "GBP"), "120 DH": (120.0, "MAD"),
                 "AED 55": (55.0, "AED"), "Free": (None, None), "": (None, None)}
        for raw, expected in cases.items():
            self.assertEqual(parse_price(raw), expected, raw)

    def test_parse_european_thousands(self):
        from .currency import parse_price

        cases = {"1.299,00 €": (1299.0, "EUR"), "2.499,99 €": (2499.99, "EUR"), "1.299 €": (1299.0, "EUR"),
                 "MAD 1.299,00": (1299.0, "MAD"), "12.500 DH": (12500.0, "MAD"), "MAD 94.09": (94.09, "MAD"),
                 "1,299.50 $": (1299.5, "USD")}
        for raw, expected in cases.items():
            self.assertEqual(parse_price(raw), expected, raw)

    def test_convert(self):
        from .currency import convert

        self.assertEqual(convert(10, "EUR", "MAD"), 108.0)
        self.assertEqual(convert(108, "MAD", "EUR"), 10.0)
        self.assertEqual(convert(5, "MAD", "MAD"), 5.0)
        self.assertIsNone(convert(5, "XYZ", "MAD"))


def p(cat, price, priority="nice"):
    return {"category": cat, "price": price, "priority": priority, "name": f"{cat}-{price}"}


class BudgetTests(SimpleTestCase):
    def test_allowances_renormalise(self):
        from .budget import category_allowances

        self.assertEqual(category_allowances(1000, ["clothing", "shoes"]), {"clothing": 636.36, "shoes": 363.64})

    def test_over_budget_keeps_one_per_category_first(self):
        from .budget import fit_to_budget

        kept, s = fit_to_budget([p("clothing", 600), p("clothing", 300), p("shoes", 500), p("shoes", 200)], 600, "MAD")
        self.assertEqual(sorted(x["name"] for x in kept), ["clothing-300", "shoes-200"])
        self.assertEqual(s, {"limit": 600, "used": 500, "currency": "MAD", "dropped": 2})

    def test_essential_before_nice(self):
        from .budget import fit_to_budget

        kept, _ = fit_to_budget([p("hair", 50), p("hair", 100, "essential"), p("hair", 90)], 160, "MAD")
        self.assertEqual(sorted(x["name"] for x in kept), ["hair-100", "hair-50"])

    def test_unpriced_kept_not_counted(self):
        from .budget import fit_to_budget

        kept, s = fit_to_budget([p("perfume", None), p("perfume", 100)], 100, "MAD")
        self.assertEqual(len(kept), 2)
        self.assertEqual(s["used"], 100)

    def test_category_too_expensive_is_dropped_and_used_never_exceeds_limit(self):
        from .budget import fit_to_budget

        kept, s = fit_to_budget([p("perfume", 900), p("hair", 80)], 100, "MAD")
        self.assertEqual([x["name"] for x in kept], ["hair-80"])
        self.assertLessEqual(s["used"], s["limit"])

    def test_exact_fit(self):
        from .budget import fit_to_budget

        kept, s = fit_to_budget([p("shoes", 250), p("shoes", 250)], 500, "MAD")
        self.assertEqual((len(kept), s["used"], s["dropped"]), (2, 500, 0))


FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "serper_shopping.json").read_text(encoding="utf-8"))["shopping"]
CLEANSER = {"category": "skincare", "name": "Hydrating Cleanser", "brand": "CeraVe", "price": 120.0,
            "currency": "MAD", "search_query": "CeraVe Hydrating Cleanser 236ml", "priority": "essential"}


class FakeFetch:
    def __init__(self, by_country=None, error=None):
        self.by_country = by_country or {}
        self.error = error
        self.calls = []

    def __call__(self, query, gl):
        self.calls.append(gl)
        if self.error:
            raise self.error
        return self.by_country.get(gl, [])


class ShoppingTests(SimpleTestCase):
    def test_pick_result_prefers_within_allowance_with_image(self):
        from .shopping import pick_result

        self.assertEqual(pick_result(FIXTURE, 160, "MAD")["source"], "SweetCare")
        self.assertEqual(pick_result(FIXTURE, 170, "MAD")["source"], "SweetCare")

    def test_pick_result_falls_back_to_cheapest_with_image(self):
        from .shopping import pick_result

        picked = pick_result(FIXTURE, 10, "MAD")
        self.assertEqual(picked["source"], "SweetCare")
        self.assertIn("imageUrl", picked)

    def test_enrich_rejects_unsafe_links_and_images(self):
        from .shopping import enrich, search_url

        bad = [{"title": "x", "source": "Evil", "link": "javascript:alert(1)", "price": "MAD 50",
                "imageUrl": "https://img.example/x.jpg"},
               {"title": "y", "source": "Evil2", "link": "https://ok.example/y", "price": "MAD 60",
                "imageUrl": "data:image/svg+xml,<svg onload=alert(1)>"}]
        [product] = enrich([CLEANSER], "MAD", {"skincare": 160}, "us", fetch=FakeFetch({"us": bad}))
        self.assertEqual(product["link"], search_url(CLEANSER["search_query"]))
        self.assertEqual(product["image_url"], "")

    def test_enrich_fills_fields(self):
        from .shopping import enrich

        [product] = enrich([CLEANSER], "MAD", {"skincare": 160}, "ma", fetch=FakeFetch({"ma": FIXTURE}))
        self.assertEqual(product["price"], 94.09)
        self.assertEqual(product["price_source"], "store")
        self.assertEqual(product["store"], "SweetCare")
        self.assertEqual(product["link"], "https://www.sweetcare.com/ma/cerave-hydrating-cleanser")
        self.assertEqual(product["image_url"], "https://img.example/sweetcare.jpg")
        self.assertFalse(product["price_converted"])

    def test_enrich_converts_foreign_currency(self):
        from .shopping import enrich

        euro = [{"title": "x", "source": "Citypharma", "link": "https://c.fr/x", "price": "€7.49",
                 "imageUrl": "https://img.example/c.jpg"}]
        [product] = enrich([CLEANSER], "MAD", {"skincare": 160}, "ma", fetch=FakeFetch({"ma": euro}))
        self.assertEqual((product["price"], product["currency"], product["price_converted"]), (80.89, "MAD", True))

    def test_enrich_local_first(self):
        from .shopping import enrich

        fetch = FakeFetch({"ma": FIXTURE, "fr": FIXTURE})
        [product] = enrich([CLEANSER], "MAD", {"skincare": 160}, "ma", fetch=fetch)
        self.assertEqual((product["origin"], product["origin_country"]), ("local", "ma"))
        self.assertEqual(fetch.calls, ["ma"])

    def test_enrich_goes_abroad_in_order(self):
        from .shopping import enrich

        fetch = FakeFetch({"us": FIXTURE})
        [product] = enrich([CLEANSER], "MAD", {"skincare": 160}, "ma", fetch=fetch)
        self.assertEqual(fetch.calls, ["ma", "fr", "us"])
        self.assertEqual((product["origin"], product["origin_country"]), ("abroad", "us"))

    def test_enrich_other_country_abroad_is_us(self):
        from .shopping import enrich

        fetch = FakeFetch()
        enrich([CLEANSER], "GBP", {"skincare": 50}, "gb", fetch=fetch)
        self.assertEqual(fetch.calls, ["gb", "us"])

    def test_enrich_nothing_anywhere_is_local_estimate(self):
        from .shopping import enrich, search_url

        [product] = enrich([CLEANSER], "MAD", {"skincare": 160}, "ma", fetch=FakeFetch())
        self.assertEqual((product["origin"], product["price_source"], product["price"]), ("local", "estimate", 120.0))
        self.assertEqual(product["link"], search_url(CLEANSER["search_query"]))
        self.assertEqual(product["image_url"], "")

    @override_settings(SERPER_API_KEY="")
    def test_enrich_without_key_or_on_error_keeps_estimate(self):
        from .shopping import enrich, search_url

        [product] = enrich([CLEANSER], "MAD", {"skincare": 160}, "ma")
        self.assertEqual(product["price_source"], "estimate")
        self.assertEqual(product["link"], search_url("CeraVe Hydrating Cleanser 236ml"))
        self.assertTrue(search_url("a b").startswith("https://www.google.com/search?tbm=shop&q=a+b"))
        [product] = enrich([CLEANSER], "MAD", {"skincare": 160}, "ma", fetch=FakeFetch(error=TimeoutError()))
        self.assertEqual((product["price_source"], product["image_url"]), ("estimate", ""))


class CountryTests(SimpleTestCase):
    def test_countries(self):
        from .countries import COUNTRIES, DEFAULT_CURRENCY, abroad_countries, flag

        self.assertEqual(set(COUNTRIES), {"ma", "fr", "es", "be", "gb", "us", "ca", "ae", "sa", "de", "it", "nl"})
        self.assertEqual(DEFAULT_CURRENCY["ma"], "MAD")
        self.assertEqual(DEFAULT_CURRENCY["ca"], "CAD")
        self.assertEqual(abroad_countries("ma"), ["fr", "us"])
        self.assertEqual(abroad_countries("de"), ["us"])
        self.assertEqual(abroad_countries("us"), [])
        self.assertEqual(flag("ma"), "\U0001F1F2\U0001F1E6")
