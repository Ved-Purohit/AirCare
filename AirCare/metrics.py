"""Session recording and movement metrics.

Units: speeds are frame-heights/second; amplitudes/workspace are % of the frame.
They are relative to camera framing, so compare a patient only against their own
earlier sessions with the camera in roughly the same place.
"""
from collections import defaultdict
from datetime import datetime
import numpy as np


def smoothness(stroke):
    """Mean/peak speed ratio of one stroke (min-jerk bell curve ~0.53; jerky multi-peak lower)."""
    if len(stroke) < 3:
        return None
    t = np.array([s[0] for s in stroke])
    y = np.array([s[1] for s in stroke])
    dt = np.diff(t)
    if np.any(dt <= 0):
        return None
    sp = np.abs(np.diff(y)) / dt
    if sp.max() <= 0:
        return None
    return float(sp.mean() / sp.max())


def _r(v, n=3):
    return None if v is None else round(float(v), n)


def _asym(a, b):
    if a is None or b is None or (a + b) == 0:
        return None
    return abs(a - b) / ((a + b) / 2) * 100


def combine(hands: dict, timing_cv=None, accuracy_pct=None, reaction_s=None) -> dict:
    """Turn per-hand stats into the session-level metrics dict (shared by recorder and demo seeder)."""
    active = [h for h in hands.values() if h.get("hits", 0) >= 3]

    def avg(key):
        vals = [h[key] for h in active if h.get(key) is not None]
        return float(np.mean(vals)) if vals else None

    m = {
        "stroke_amp": avg("stroke_amp"),
        "workspace_h": avg("workspace_h"),
        "mean_speed": avg("mean_speed"),
        "smoothness": avg("smoothness"),
        "timing_cv": timing_cv,
        "asymmetry_speed": None,
        "asymmetry_amp": None,
        "accuracy_pct": accuracy_pct,
        "reaction_s": reaction_s,
    }
    L, R = hands.get("Left"), hands.get("Right")
    if L and R and L.get("hits", 0) >= 3 and R.get("hits", 0) >= 3:
        m["asymmetry_speed"] = _asym(L.get("mean_speed"), R.get("mean_speed"))
        m["asymmetry_amp"] = _asym(L.get("stroke_amp"), R.get("stroke_amp"))
    return {k: _r(v) for k, v in m.items()}


class SessionRecorder:
    def __init__(self, patient: str, mode: str, guided: bool):
        self.patient, self.mode, self.guided = patient, mode, guided
        self.started_at = datetime.now().isoformat(timespec="seconds")
        self.t0 = None
        self.t_last = 0.0
        self.pos = defaultdict(list)
        self.hits = []
        self.targets = []

    def add_position(self, hand, t, x, y):
        if self.t0 is None:
            self.t0 = t
        self.t_last = t
        self.pos[hand].append((x, y))

    def add_hit(self, hand, strike, zone, correct=None):
        """zone: drum that was hit (None = landed outside every drum).
        correct: guided mode only. True = the lit target, False = wrong drum or outside."""
        self.hits.append({"hand": hand, "t": strike.t, "zone": zone, "v": strike.velocity,
                          "travel": strike.travel, "smooth": smoothness(strike.stroke),
                          "x": strike.x, "correct": correct})

    def add_target(self, hit: bool, reaction=None):
        self.targets.append((hit, reaction))

    def _hand_stats(self, hand):
        hs = [h for h in self.hits if h["hand"] == hand]
        pos = np.array(self.pos.get(hand, []))
        st = {"hits": len(hs), "mean_speed": None, "peak_speed": None, "stroke_amp": None,
              "workspace_v": None, "workspace_h": None, "smoothness": None}
        if hs:
            v = np.array([h["v"] for h in hs])
            st["mean_speed"] = float(v.mean())
            st["peak_speed"] = float(np.percentile(v, 90))
            st["stroke_amp"] = float(np.mean([h["travel"] for h in hs]) * 100)
            sm = [h["smooth"] for h in hs if h["smooth"] is not None]
            st["smoothness"] = float(np.mean(sm)) if sm else None
        if len(pos) >= 10:
            st["workspace_v"] = float((np.percentile(pos[:, 1], 95) - np.percentile(pos[:, 1], 5)) * 100)
            st["workspace_h"] = float((np.percentile(pos[:, 0], 95) - np.percentile(pos[:, 0], 5)) * 100)
        return {k: (_r(v) if k != "hits" else v) for k, v in st.items()}

    def _timing_cv(self):
        cvs = []
        for hand in {h["hand"] for h in self.hits}:
            ts = sorted(h["t"] for h in self.hits if h["hand"] == hand)
            iv = [b - a for a, b in zip(ts, ts[1:]) if b - a < 2.0]
            if len(iv) >= 5 and np.mean(iv) > 0:
                cvs.append(np.std(iv) / np.mean(iv))
        return float(np.mean(cvs)) if cvs else None

    def summary(self) -> dict:
        hands = {h: self._hand_stats(h) for h in ("Left", "Right") if self.pos.get(h)}
        dur = max(0.0, self.t_last - (self.t0 or 0))
        total = len(self.hits)
        in_zone = sum(1 for h in self.hits if h["zone"])
        judged = [h for h in self.hits if h["correct"] is not None]
        if judged:      # guided: every strike counts, wrong drum and off-drum are both misses
            acc = 100 * sum(1 for h in judged if h["correct"]) / len(judged)
        else:           # free play: strikes that land on a drum vs. in empty space
            acc = 100 * in_zone / total if total else None
        rts = [r for ok, r in self.targets if ok and r is not None]
        return {
            "schema": 1, "patient": self.patient, "started_at": self.started_at,
            "duration_s": round(dur, 1), "mode": self.mode, "guided": self.guided or bool(judged),
            "synthetic": False, "total_hits": total,
            "wrong_drum_hits": sum(1 for h in judged if h["zone"] and not h["correct"]),
            "off_drum_hits": total - in_zone,
            "missed_targets": sum(1 for ok, _ in self.targets if not ok),
            "hits_per_min": round(total / dur * 60, 1) if dur > 0 else 0,
            "hands": hands,
            "metrics": combine(hands, self._timing_cv(), acc, float(np.mean(rts)) if rts else None),
        }
