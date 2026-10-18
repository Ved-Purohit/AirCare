import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analytics import analyze
from metrics import combine, smoothness


def sess(i, left_factor=1.0, days_ago=0):
    h = lambda f: {"hits": 60, "mean_speed": 1.5 * f, "peak_speed": 2, "stroke_amp": 7 * f,
                   "workspace_v": 30, "workspace_h": 50 * f, "smoothness": 0.5}
    hands = {"Left": h(left_factor), "Right": h(1.0)}
    return {"started_at": (datetime.now() - timedelta(days=days_ago + (10 - i))).replace(microsecond=0).isoformat(),
            "guided": False, "hands": hands, "metrics": combine(hands, 0.25, 80, None)}


class AnalyticsTests(unittest.TestCase):
    def test_stable_patient_not_flagged(self):
        a = analyze([sess(i) for i in range(8)])
        self.assertEqual(a["status"], "ok")
        self.assertEqual(a["flags"], [])

    def test_one_sided_drop_is_flagged_with_reason(self):
        a = analyze([sess(i) for i in range(7)] + [sess(7, left_factor=0.6)])
        self.assertEqual(a["status"], "alert")
        labels = {f["label"] for f in a["flags"]}
        self.assertIn("Stroke amplitude", labels)
        self.assertIn("Left-right amplitude gap", labels)
        self.assertTrue(all(f["text"] for f in a["flags"]))

    def test_baseline_needs_history(self):
        self.assertEqual(analyze([sess(0), sess(1)])["status"], "building_baseline")
        self.assertEqual(analyze([])["status"], "no_data")

    def test_gradual_decline_caught_before_alert(self):
        s = [sess(i) for i in range(4)] + [sess(4 + k, left_factor=1 - 0.04 * (k + 1)) for k in range(4)]
        a = analyze(s)
        self.assertIn(a["status"], ("watch", "alert"))

    def test_engagement_gap(self):
        a = analyze([sess(i, days_ago=12) for i in range(6)])
        self.assertTrue(any(f["metric"] == "engagement" for f in a["flags"]))

    def test_smoothness_ratio(self):
        self.assertIsNone(smoothness([(0, 0), (1, 1)]))
        bell = [(i / 10, (1 - __import__("math").cos(3.14159 * i / 10)) / 2) for i in range(11)]
        self.assertTrue(0.45 < smoothness(bell) < 0.65)


if __name__ == "__main__":
    unittest.main()
