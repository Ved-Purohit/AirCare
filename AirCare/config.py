"""Shared configuration for AirCare."""
from dataclasses import dataclass, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOUND_DIR = ROOT / "sounds"
DATA_DIR = ROOT / "data"


@dataclass(frozen=True)
class StrikeConfig:
    """Thresholds for strike detection. Speeds are in frame-heights per second."""
    v_start: float = 0.40       # movement speed that starts a stroke
    v_min: float = 0.65        # peak speed needed to count as a strike
    v_max: float = 3.9          # peak speed that maps to full volume
    decel_frac: float = 0.5     # strike fires when speed falls below this share of peak
    direction_change_deg: float = 55.0  # sharp turn angle that can trigger without a stop
    min_travel: float = 0.05    # minimum movement distance (fraction of frame diagonal)
    cooldown_s: float = 0.08    # tiny refractory time; the stroke state machine does the real work
    max_stroke_s: float = 0.7   # abandon a stroke that takes longer than this
    pos_alpha: float = 0.8      # position smoothing (1 = none)
    vel_alpha: float = 0.7      # velocity smoothing (1 = none)
    track_gap_s: float = 0.25   # reset if tracking is lost for longer than this
    end_lead_s: float = 0.025   # hit spot = current position pushed this far along the motion (where it ends)

    def scaled(self, sensitivity: float) -> "StrikeConfig":
        """sensitivity > 1 makes smaller / slower movements count (use for rehab)."""
        s = max(0.2, sensitivity)
        return replace(self, v_start=self.v_start / s, v_min=self.v_min / s,
                       v_max=self.v_max / s, min_travel=self.min_travel / s)


# name: (x1, y1, x2, y2, BGR colour, sound file) -- coordinates are fractions of the frame.
ZONES = {
    "KICK":    (0.03, 0.18, 0.30, 0.46, (70, 80, 235),  "kick.wav"),
    "SNARE":   (0.35, 0.18, 0.62, 0.46, (255, 120, 60), "snare.wav"),
    "TOM":     (0.67, 0.18, 0.97, 0.46, (40, 210, 220), "tom_mid.wav"),
    "CYMBAL":  (0.03, 0.60, 0.30, 0.90, (90, 220, 90),  "crash.wav"),
    "HI-HAT":  (0.35, 0.60, 0.62, 0.90, (230, 200, 60), "hihat.wav"),
    "COWBELL": (0.67, 0.60, 0.97, 0.90, (200, 120, 255), "cowbell.wav"),
}

HIT_MARGIN = 0.03   # forgiveness around each drum, as a fraction of the frame


def zone_at(x: float, y: float, margin: float = 0.0):
    """Drum under (x, y). With a margin, overlapping drums go to the one whose centre is nearest."""
    best, best_d = None, 1e9
    for name, (x1, y1, x2, y2, _c, _s) in ZONES.items():
        if x1 - margin <= x <= x2 + margin and y1 - margin <= y <= y2 + margin:
            d = (x - (x1 + x2) / 2) ** 2 + (y - (y1 + y2) / 2) ** 2
            if d < best_d:
                best, best_d = name, d
    return best
