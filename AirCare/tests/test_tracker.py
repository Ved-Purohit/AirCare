import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tracker import HandTracker, _HandState


def hand(index_extended=True):
    pts = np.zeros((21, 2), dtype=np.float32)
    pts[0] = (100, 300)
    pts[9] = (100, 200)
    pts[5] = (75, 210)
    pts[6] = (75, 160 if index_extended else 195)
    pts[8] = (75, 90 if index_extended else 180)
    return pts


class PalmTrackingTests(unittest.TestCase):
    def test_palm_is_selected_and_smoothed(self):
        tracker = object.__new__(HandTracker)
        state = _HandState()
        first, source = tracker._track(state, hand(True))
        second, source = tracker._track(state, hand(True) + np.array([30, 0], dtype=np.float32))
        self.assertEqual(source, "palm")
        self.assertEqual(first[1], second[1])
        self.assertGreater(second[0], first[0])

    def test_closed_hand_uses_palm(self):
        tracker = object.__new__(HandTracker)
        point, source = tracker._track(_HandState(), hand(False))
        self.assertEqual(source, "palm")
        self.assertEqual(tuple(point), (100, 200))


if __name__ == "__main__":
    unittest.main()
