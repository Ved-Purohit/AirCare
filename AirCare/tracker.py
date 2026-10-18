"""MediaPipe hand tracker with deliberate closed-fist/open-palm gestures."""
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class Point:
    label: str
    x: float
    y: float
    px: int
    py: int
    source: str = "palm"
    palm: tuple = None
    gesture: str = "unknown"
    gesture_event: bool = False


class _HandState:
    def __init__(self):
        self.filtered = None
        self.gesture = "unknown"
        self.gesture_event = False


def _finger_is_extended(pts, tip, pip, mcp, wrist):
    """Return whether one finger is clearly extended from the palm."""
    return (np.linalg.norm(pts[tip] - wrist) > np.linalg.norm(pts[pip] - wrist) * 1.10
            and np.linalg.norm(pts[tip] - pts[mcp]) > np.linalg.norm(pts[pip] - pts[mcp]) * 1.10)


def palm_gesture(pts):
    """Classify a hand with hysteresis-friendly open/closed thresholds."""
    wrist = pts[0]
    fingers = sum(
        _finger_is_extended(pts, tip, pip, mcp, wrist)
        for tip, pip, mcp in ((8, 6, 5), (12, 10, 9), (16, 14, 13), (20, 18, 17))
    )
    if fingers >= 4:
        return "open"
    if fingers <= 1:
        return "closed"
    return "transition"


class HandTracker:
    def __init__(self):
        import mediapipe as mp

        self.hands = mp.solutions.hands.Hands(
            static_image_mode=False, max_num_hands=2, model_complexity=0,
            min_detection_confidence=0.6, min_tracking_confidence=0.5)
        self.states = {}
        self.debug = []
        self.hint = "Close your fist, place your palm over a drum, then open your hand"

    def _track(self, st, pts):
        wrist, palm = pts[0], pts[9]
        s = max(float(np.linalg.norm(palm - wrist)), 1e-3)
        observed = palm_gesture(pts)
        previous = st.gesture
        if observed in ("open", "closed"):
            st.gesture = observed
        st.gesture_event = previous == "closed" and st.gesture == "open"
        target = pts[9]
        if st.filtered is None:
            st.filtered = target.astype(np.float32)
        else:
            # Keep the hand responsive during a strike while removing landmark jitter.
            delta = float(np.linalg.norm(target - st.filtered))
            alpha = 0.62 if delta > 0.035 * s else 0.32
            st.filtered = alpha * target + (1 - alpha) * st.filtered
        return st.filtered, "palm"

    def update(self, frame):
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        res = self.hands.process(rgb)
        self.debug = []
        found = []
        if res.multi_hand_landmarks:
            for lm, hd in zip(res.multi_hand_landmarks, res.multi_handedness):
                pts = np.array([[p.x * w, p.y * h] for p in lm.landmark], np.float32)
                found.append([pts, hd.classification[0].label])
        if len(found) == 2:
            found.sort(key=lambda f: f[0][9][0])
            found[0][1], found[1][1] = "Left", "Right"
        out = []
        for pts, label in found:
            state = self.states.setdefault(label, _HandState())
            tip, src = self._track(state, pts)
            x, y = min(max(tip[0], 0), w - 1), min(max(tip[1], 0), h - 1)
            out.append(Point(label, x / w, y / h, int(x), int(y), src,
                             (int(pts[9][0]), int(pts[9][1])),
                             state.gesture, state.gesture_event))
        return out
