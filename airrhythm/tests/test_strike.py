import math
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import StrikeConfig, zone_at
from strike import StrikeDetector, velocity_to_volume


def run(fn, seconds, fps=30):
    det, hits = StrikeDetector(), []
    for i in range(int(seconds * fps)):
        t = i / fps
        x, y = fn(t)
        s = det.update(t, x, y)
        if s:
            hits.append(s)
    return hits


class StrikeTests(unittest.TestCase):
    def test_sharp_direction_change_triggers_without_stopping(self):
        cfg = StrikeConfig(direction_change_deg=30)
        det = StrikeDetector(cfg)
        points = [
            (0.20, 0.50), (0.27, 0.50), (0.34, 0.50),
            (0.40, 0.57), (0.46, 0.64),
        ]
        hits = []
        for i, (x, y) in enumerate(points):
            hit = det.update(i / 30, x, y)
            if hit:
                hits.append(hit)
        self.assertEqual(len(hits), 1)
        self.assertAlmostEqual(hits[0].x, 0.40, delta=0.04)
        self.assertAlmostEqual(hits[0].y, 0.57, delta=0.04)

    def test_sharp_movement_can_trigger_in_either_direction(self):
        hits = run(lambda t: (0.3, 0.5 + 0.15 * math.sin(2 * math.pi * 2 * t)), 5)   # 2 strokes/s
        self.assertTrue(18 <= len(hits) <= 20, len(hits))
        gaps = [b.t - a.t for a, b in zip(hits, hits[1:])]
        self.assertTrue(all(0.15 < g < 0.35 for g in gaps), gaps)

    def test_sharp_movement_lands_at_its_endpoint(self):
        hits = run(lambda t: (0.3, 0.5 + 0.15 * math.sin(2 * math.pi * 2 * t)), 3)
        self.assertTrue(all(0.25 < h.y < 0.75 for h in hits), [h.y for h in hits])

    def test_still_hand_and_jitter_do_not_trigger(self):
        rnd = random.Random(1)
        self.assertEqual(run(lambda t: (0.5, 0.5), 3), [])
        self.assertEqual(run(lambda t: (0.5 + rnd.gauss(0, .003), 0.5 + rnd.gauss(0, .003)), 5), [])

    def test_slow_drift_does_not_trigger(self):
        self.assertEqual(run(lambda t: (0.5, 0.3 + 0.05 * t), 4), [])

    def test_harder_hit_is_louder(self):
        soft = run(lambda t: (0.3, 0.5 + 0.10 * math.sin(2 * math.pi * 1.6 * t)), 3)
        hard = run(lambda t: (0.3, 0.5 + 0.18 * math.sin(2 * math.pi * 2.5 * t)), 3)
        cfg = StrikeConfig()
        self.assertTrue(soft and hard)
        self.assertGreater(velocity_to_volume(hard[0].velocity, cfg), velocity_to_volume(soft[0].velocity, cfg))

    def test_fast_playing_like_real_drums(self):
        # 60 fps camera, 7 strokes per second: every stroke should be a hit, none doubled
        hits = run(lambda t: (0.3, 0.6 + 0.07 * math.sin(2 * math.pi * 7 * t)), 3, fps=60)
        self.assertGreaterEqual(len(hits), int(3 * 7 * 0.55), len(hits))
        self.assertLessEqual(len(hits), 3 * 7 + 1, len(hits))

    def test_30fps_still_handles_a_roll(self):
        hits = run(lambda t: (0.3, 0.6 + 0.09 * math.sin(2 * math.pi * 4.5 * t)), 3, fps=30)
        self.assertGreaterEqual(len(hits), int(3 * 4.5 * 0.4), len(hits))

    def test_hit_spot_is_where_the_stroke_ends(self):
        # strikes land at the final point regardless of movement direction
        for end_y, zone in ((0.40, "TOM MID"), (0.75, "FLOOR TOM")):
            x0 = 0.63
            hits = run(lambda t, e=end_y: (x0, (e - 0.12) + 0.12 * (0.5 - 0.5 * math.cos(2 * math.pi * 2 * t))), 3)
            self.assertTrue(hits)
            from config import HIT_MARGIN
            expected = "SNARE" if end_y < 0.5 else "HI-HAT"
            self.assertTrue(all(zone_at(h.x, h.y, HIT_MARGIN) == expected for h in hits))

    def test_sharp_upward_tap_lands_at_resting_position(self):
        det = StrikeDetector()
        hits = []
        ys = [0.70] * 8 + [0.66, 0.60, 0.55] + [0.55] * 12
        for i, y in enumerate(ys):
            hit = det.update(i / 30, 0.5, y)
            if hit:
                hits.append(hit)
        self.assertEqual(len(hits), 1)
        self.assertLess(hits[0].y, 0.62)

    def test_tracking_loss_resets(self):
        det = StrikeDetector()
        det.update(0.0, 0.5, 0.2)
        self.assertIsNone(det.update(1.0, 0.5, 0.9))   # big jump after a gap is not a strike

    def test_zones(self):
        self.assertEqual(zone_at(0.3, 0.65), "CYMBAL")
        self.assertEqual(zone_at(0.6, 0.3), "SNARE")
        self.assertIsNone(zone_at(0.5, 0.5))
        self.assertEqual(zone_at(0.8, 0.7, margin=0.03), "COWBELL")


if __name__ == "__main__":
    unittest.main()
