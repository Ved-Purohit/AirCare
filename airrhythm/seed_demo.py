"""Creates SYNTHETIC patient history so the clinician dashboard can be demoed without weeks of data.
Run: python seed_demo.py   then   python dashboard.py
"""
from datetime import datetime, timedelta
import numpy as np
from metrics import combine
from storage import save_session


def make_hands(rng, prog, left_factor=1.0, smooth_factor=1.0, hits=70):
    def hand(amp, speed, smooth, ws):
        return {"hits": int(hits + rng.integers(-8, 8)), "mean_speed": round(speed, 3),
                "peak_speed": round(speed * 1.5, 3), "stroke_amp": round(amp, 3),
                "workspace_v": round(ws * 0.7, 3), "workspace_h": round(ws, 3), "smoothness": round(smooth, 3)}
    n = lambda s: rng.normal(0, s)
    right = hand(8.0 + 1.0 * prog + n(0.25), 1.75 + 0.15 * prog + n(0.05), 0.50 + 0.02 * prog + n(0.01), 52 + 3 * prog + n(1))
    left = hand((5.6 + 2.3 * prog + n(0.25)) * left_factor, (1.25 + 0.4 * prog + n(0.05)) * left_factor,
                (0.46 + 0.04 * prog + n(0.01)) * smooth_factor, (40 + 9 * prog + n(1)) * (0.5 + 0.5 * left_factor))
    return {"Left": left, "Right": right}


def seed(patient="demo_patient", n=11, decline_last=2, seed_val=3):
    rng = np.random.default_rng(seed_val)
    end = datetime.now() - timedelta(days=1)
    for i in range(n):
        when = end - timedelta(days=(n - 1 - i) * 3)
        declining = i >= n - decline_last
        k = (i - (n - decline_last) + 1) if declining else 0
        lf = 1.0 - 0.17 * k if declining else 1.0
        sf = 1.0 - 0.07 * k if declining else 1.0
        prog = min(1.0, i / max(1, n - decline_last - 1))
        guided = i % 2 == 0
        hands = make_hands(rng, prog, lf, sf)
        acc = (68 + 14 * prog + rng.normal(0, 2) - (6 * k if declining else 0)) if guided else None
        rt = (1.9 - 0.4 * prog + rng.normal(0, 0.05) + (0.25 * k if declining else 0)) if guided else None
        dur = float(180 + rng.integers(-20, 20))
        hits = sum(h["hits"] for h in hands.values())
        save_session({
            "schema": 1, "patient": patient, "started_at": when.replace(microsecond=0).isoformat(),
            "duration_s": dur, "mode": "hands", "guided": guided, "synthetic": True,
            "total_hits": hits, "hits_per_min": round(hits / dur * 60, 1), "hands": hands,
            "metrics": combine(hands, round(0.30 - 0.05 * prog + rng.normal(0, 0.01), 3), acc, rt),
        })
    print(f"Seeded {n} synthetic sessions for '{patient}' (last {decline_last} show a left-side decline).")


if __name__ == "__main__":
    seed()
    seed("demo_stable", n=8, decline_last=0, seed_val=11)
