"""Early-warning analytics: compares each session with the patient's OWN baseline.

Method (deliberately explainable, so a therapist can see why something was flagged):
  1. Baseline  = median of the patient's first (up to) 3 sessions of the same type.
  2. Latest session vs baseline, scored in the 'worse' direction per metric.
  3. Trend     = linear fit over the last 6 sessions, to catch slow drift before it crosses a threshold.
  4. Engagement = days since last session.
Nothing here is diagnostic; flags are prompts for a human to take a look.
"""
from datetime import datetime
import numpy as np

METRICS = {
    "stroke_amp": dict(label="Stroke amplitude", unit="% of frame height", better="higher", kind="rel", warn=0.15, alert=0.30,
                       hint="Shorter strokes can reflect reduced shoulder, elbow or wrist range, pain avoidance, or fatigue."),
    "workspace_h": dict(label="Horizontal reach", unit="% of frame width", better="higher", kind="rel", warn=0.15, alert=0.30,
                        hint="A narrower working area can mean the patient is avoiding reaching to one side."),
    "mean_speed": dict(label="Movement speed", unit="frame-heights/s", better="higher", kind="rel", warn=0.20, alert=0.35,
                       hint="Slower strokes can accompany weakness, stiffness, fatigue or low motivation."),
    "smoothness": dict(label="Movement smoothness", unit="ratio, 0-1", better="higher", kind="rel", warn=0.12, alert=0.25,
                       hint="Jerkier strokes can indicate reduced motor control or tremor."),
    "timing_cv": dict(label="Rhythm variability", unit="coefficient of variation", better="lower", kind="rel", warn=0.25, alert=0.50,
                      hint="Less steady timing can indicate reduced coordination or attention."),
    "asymmetry_speed": dict(label="Left-right speed gap", unit="%", better="lower", kind="abs", warn=10, alert=20,
                            hint="A growing gap between sides can point to a one-sided deficit."),
    "asymmetry_amp": dict(label="Left-right amplitude gap", unit="%", better="lower", kind="abs", warn=10, alert=20,
                          hint="A growing gap between sides can point to a one-sided range-of-motion problem."),
    "accuracy_pct": dict(label="Target accuracy", unit="%", better="higher", kind="rel", warn=0.15, alert=0.30,
                         hint="Missing targets more often can reflect reduced coordination, vision or attention."),
    "reaction_s": dict(label="Reaction time", unit="s", better="lower", kind="rel", warn=0.25, alert=0.50,
                       hint="Slower reactions can reflect fatigue, attention or processing changes."),
}


def _worsening(spec, base, val):
    """Positive = got worse. Relative fraction for 'rel', percentage points for 'abs'."""
    if base is None or val is None:
        return None
    if spec["kind"] == "abs":
        return (val - base) if spec["better"] == "lower" else (base - val)
    if base == 0:
        return None
    return (base - val) / abs(base) if spec["better"] == "higher" else (val - base) / abs(base)


def _severity(spec, w):
    if w is None:
        return None
    if w >= spec["alert"]:
        return "alert"
    if w >= spec["warn"]:
        return "watch"
    return None


def _fmt(v):
    return "n/a" if v is None else (f"{v:.0f}" if abs(v) >= 100 else f"{v:.2g}" if abs(v) < 1 else f"{v:.1f}")


def _median(vals):
    vals = [v for v in vals if v is not None]
    return float(np.median(vals)) if len(vals) >= 2 else None


def _describe(spec, w, base, val):
    if spec["kind"] == "abs":
        how = f"{abs(w):.0f} points {'above' if spec['better'] == 'lower' else 'below'} baseline"
    else:
        how = f"{abs(w) * 100:.0f}% {'below' if spec['better'] == 'higher' else 'above'} baseline"
    return f"{spec['label']} is {how} ({_fmt(base)} to {_fmt(val)} {spec['unit']}). {spec['hint']}"


def analyze(sessions, now=None):
    now = now or datetime.now()
    out = {"n_sessions": len(sessions), "status": "no_data", "flags": [], "cards": {}, "baseline_n": 0}
    if not sessions:
        return out
    latest = sessions[-1]
    if latest.get("mode"):
        peers = [s for s in sessions if s.get("mode") == latest.get("mode")]
    else:
        peers = [s for s in sessions if s.get("guided") == latest.get("guided")]
    if len(peers) < 3:
        peers = sessions
    base_sessions = peers[:-1][:3]
    out["baseline_n"] = len(base_sessions)
    have_base = len(base_sessions) >= 2
    flags = []

    for key, spec in METRICS.items():
        series = [(s.get("metrics") or {}).get(key) for s in peers]
        base = _median([(s.get("metrics") or {}).get(key) for s in base_sessions]) if have_base else None
        val = series[-1]
        w = _worsening(spec, base, val)
        sev = _severity(spec, w)
        card = {"spec": spec, "series": series, "baseline": base, "latest": val, "worsen": w, "severity": sev}
        if sev:
            flags.append({"metric": key, "label": spec["label"], "severity": sev, "kind": "change",
                          "text": _describe(spec, w, base, val)})
        elif have_base:   # slow-drift check on the last 6 sessions
            recent = [(i, v) for i, v in enumerate(series[-6:]) if v is not None]
            if len(recent) >= 4 and base is not None:
                xs = np.array([i for i, _ in recent], float)
                ys = np.array([v for _, v in recent], float)
                slope = np.polyfit(xs, ys, 1)[0]
                drift = _worsening(spec, base, base + slope * (xs[-1] - xs[0]))
                thr = spec["warn"] / 2
                if drift is not None and drift >= thr:
                    card["severity"] = "watch"
                    pct = f"{drift * 100:.0f}%" if spec["kind"] == "rel" else f"{drift:.0f} points"
                    flags.append({"metric": key, "label": spec["label"], "severity": "watch", "kind": "trend",
                                  "text": f"{spec['label']} has been drifting the wrong way (about {pct}) over the last "
                                          f"{len(recent)} sessions. Not past the alert line yet, which is the point of catching it now."})
        out["cards"][key] = card

    try:
        days = (now - datetime.fromisoformat(latest["started_at"])).days
        if days >= 7:
            flags.append({"metric": "engagement", "label": "Engagement", "severity": "watch", "kind": "gap",
                          "text": f"No session in {days} days. Reduced engagement is itself an early signal worth a check-in."})
    except (KeyError, ValueError):
        pass

    flags.sort(key=lambda f: (f["severity"] != "alert", f["kind"] != "change"))
    out["flags"] = flags
    if not have_base:
        out["status"] = "building_baseline"
    elif any(f["severity"] == "alert" for f in flags):
        out["status"] = "alert"
    elif flags:
        out["status"] = "watch"
    else:
        out["status"] = "ok"
    return out
