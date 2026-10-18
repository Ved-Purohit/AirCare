"""Direction-agnostic strike detection for sharp movements and sharp turns."""
import math
from dataclasses import dataclass, field
from config import StrikeConfig


@dataclass
class Strike:
    t: float
    x: float
    y: float
    velocity: float          # peak downward speed, frame-heights/s
    travel: float            # downward travel of the stroke, fraction of frame height
    stroke: list = field(default_factory=list)   # [(t, y), ...] for smoothness analysis


class StrikeDetector:
    def __init__(self, cfg: StrikeConfig = None):
        self.cfg = cfg or StrikeConfig()
        self.reset()

    def reset(self):
        self._init = False
        self.state = "idle"
        self.cooldown_until = 0.0
        self.vx = self.vy = 0.0
        self.prev_vx = self.prev_vy = 0.0

    def update(self, t: float, x: float, y: float):
        """Feed one tracked point (normalised coords, y grows downward). Returns Strike or None."""
        c = self.cfg
        if not self._init or t - self.t > c.track_gap_s:
            self._init = True
            self.sx, self.sy, self.t = x, y, t
            self.vx = self.vy = 0.0
            self.state = "idle"
            return None
        dt = t - self.t
        if dt < 1e-3:
            return None
        a, b = c.pos_alpha, c.vel_alpha
        nx = a * x + (1 - a) * self.sx
        ny = a * y + (1 - a) * self.sy
        self.vx = b * (nx - self.sx) / dt + (1 - b) * self.vx
        self.vy = b * (ny - self.sy) / dt + (1 - b) * self.vy
        old_vx, old_vy = self.prev_vx, self.prev_vy
        old_speed = (old_vx * old_vx + old_vy * old_vy) ** 0.5
        prev_x, prev_y, prev_t = self.sx, self.sy, self.t
        self.sx, self.sy, self.t = nx, ny, t

        if t < self.cooldown_until:
            return None

        speed = (self.vx * self.vx + self.vy * self.vy) ** 0.5
        if self.state == "idle":
            if speed > c.v_start:
                self.state = "down"
                self.start_x, self.start_y, self.start_t = prev_x, prev_y, prev_t
                self.peak = speed
                self.samples = [(prev_t, prev_y), (t, ny)]
            self.prev_vx, self.prev_vy = self.vx, self.vy
            return None

        self.samples.append((t, ny))
        self.peak = max(self.peak, speed)
        turned = False
        if old_speed >= c.v_start and speed >= c.v_start:
            dot = old_vx * self.vx + old_vy * self.vy
            cos_angle = dot / max(old_speed * speed, 1e-9)
            turned = math.degrees(math.acos(max(-1.0, min(1.0, cos_angle)))) >= c.direction_change_deg
        self.prev_vx, self.prev_vy = self.vx, self.vy
        if speed <= c.decel_frac * self.peak:
            travel = ((nx - self.start_x) ** 2 + (ny - self.start_y) ** 2) ** 0.5
            if self.peak >= c.v_min and travel >= c.min_travel:
                self.state = "idle"
                self.cooldown_until = t + c.cooldown_s
                hx, hy = nx, ny
                return Strike(t, min(1.0, max(0.0, hx)),
                              min(1.0, max(0.0, hy)), self.peak, travel, self.samples)
            self.state = "idle"
            return None
        if turned:
            travel = ((nx - self.start_x) ** 2 + (ny - self.start_y) ** 2) ** 0.5
            if self.peak >= c.v_min and travel >= c.min_travel:
                self.state = "idle"
                self.cooldown_until = t + c.cooldown_s
                return Strike(t, min(1.0, max(0.0, nx)),
                              min(1.0, max(0.0, ny)), self.peak, travel, self.samples)
        if t - self.start_t > c.max_stroke_s:
            self.state = "idle"
        return None


def velocity_to_volume(v: float, cfg: StrikeConfig) -> float:
    """Map peak strike speed to 0.15..1.0 volume (soft touch = quiet, hard hit = loud)."""
    x = (v - cfg.v_min) / (cfg.v_max - cfg.v_min)
    x = min(1.0, max(0.0, x))
    return 0.15 + 0.85 * x ** 0.7
