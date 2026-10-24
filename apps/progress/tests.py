from django.test import SimpleTestCase

from .rules import XP_EVENTS, level_for, xp_for_status_change, xp_threshold


class LevelRulesTests(SimpleTestCase):
    def test_thresholds(self):
        self.assertEqual([xp_threshold(n) for n in (1, 2, 3, 4)], [0, 100, 300, 600])

    def test_level_boundaries(self):
        self.assertEqual(level_for(0)["level"], 1)
        self.assertEqual(level_for(99)["level"], 1)
        self.assertEqual(level_for(100)["level"], 2)
        self.assertEqual(level_for(300)["level"], 3)

    def test_progress_fields(self):
        info = level_for(150)
        self.assertEqual(info["xp_into_level"], 50)
        self.assertEqual(info["xp_for_next"], 200)
        self.assertEqual(info["xp_to_next"], 150)
        self.assertEqual(info["progress_pct"], 25)
        self.assertEqual(info["title"], "Trend Seeker")

    def test_bad_input_is_safe(self):
        self.assertEqual(level_for(None)["level"], 1)
        self.assertEqual(level_for(-50)["xp"], 0)
        self.assertEqual(level_for(10**7)["title"], "Mraya Icon")

    def test_status_xp_awarded_once(self):
        self.assertEqual(xp_for_status_change({"xp_events": []}, "started"),
                         ("product_started", XP_EVENTS["product_started"]))
        self.assertEqual(xp_for_status_change({"xp_events": ["product_started"]}, "started"), (None, 0))
        self.assertEqual(xp_for_status_change({}, "not_yet"), (None, 0))
