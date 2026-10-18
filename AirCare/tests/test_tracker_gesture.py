import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tracker import palm_gesture


def hand(finger_tips):
    pts = np.zeros((21, 2), dtype=np.float32)
    pts[0] = (0.0, 0.0)
    for mcp, pip, tip, x, extended in finger_tips:
        pts[mcp] = (x, -1.0)
        pts[pip] = (x, -2.0)
        pts[tip] = (x, -3.0 if extended else -1.2)
    return pts


class GestureTests(unittest.TestCase):
    def test_four_extended_fingers_are_open(self):
        fingers = [(5, 6, 8, -1.5, True), (9, 10, 12, -0.5, True),
                   (13, 14, 16, 0.5, True), (17, 18, 20, 1.5, True)]
        self.assertEqual(palm_gesture(hand(fingers)), "open")

    def test_closed_fist_is_closed(self):
        fingers = [(5, 6, 8, -1.5, False), (9, 10, 12, -0.5, False),
                   (13, 14, 16, 0.5, False), (17, 18, 20, 1.5, False)]
        self.assertEqual(palm_gesture(hand(fingers)), "closed")

    def test_partial_hand_is_transition(self):
        fingers = [(5, 6, 8, -1.5, True), (9, 10, 12, -0.5, True),
                   (13, 14, 16, 0.5, False), (17, 18, 20, 1.5, False)]
        self.assertEqual(palm_gesture(hand(fingers)), "transition")


if __name__ == "__main__":
    unittest.main()
