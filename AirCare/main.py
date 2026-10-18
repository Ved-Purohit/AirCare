"""AirCare - webcam air drumming for rehabilitation.

  python main.py --patient alex                 # free play
  python main.py --patient alex --mode guided   # one highlighted target
  python main.py --patient alex --mode timed    # two two-second targets
  python main.py --patient alex --mode reaction # two active drums, replace on hit
Keys: q finish & save | m mute | d debug view
"""
import argparse
import random
import time

import cv2

from camera import Camera
from config import HIT_MARGIN, SOUND_DIR, ZONES, StrikeConfig, zone_at
from metrics import SessionRecorder
from storage import save_session
from strike import Strike, velocity_to_volume

WIN = "AirCare"
SRC_COLOR = {"palm": (255, 255, 255)}


class TargetMode:
    """Target rules shared by guided, timed, and reaction gameplay."""
    def __init__(self, rec, kind):
        self.rec, self.kind = rec, kind
        self.active = {}
        self.score = 0
        self.last = None

    def _pick(self):
        choices = [z for z in ZONES if z not in self.active and z != self.last]
        return random.choice(choices or [z for z in ZONES if z not in self.active])

    def _add(self, now):
        zone = self._pick()
        self.active[zone] = now
        self.last = zone

    def start(self, now):
        count = {"guided": 1, "timed": 2, "reaction": 2}[self.kind]
        for _ in range(count):
            self._add(now)

    def on_strike(self, zone, now):
        if zone in self.active:
            started = self.active.pop(zone)
            self.rec.add_target(True, now - started)
            self.score += 1
            self._add(now)
            return "correct"
        return "wrong" if zone else "off"

    def tick(self, now):
        if self.kind == "guided":
            expired = [z for z, started in self.active.items() if now - started > 8.0]
            for zone in expired:
                self.active.pop(zone, None)
                self.rec.add_target(False)
                self._add(now)
        elif self.kind == "timed":
            expired = [z for z, started in self.active.items() if now - started > 2.0]
            for zone in expired:
                self.active.pop(zone, None)
                self.rec.add_target(False)
                self._add(now)
        # Reaction targets stay visible until hit; a successful hit replaces one.

    @property
    def target(self):
        return next(iter(self.active), None) if self.kind == "guided" else None


def load_sounds():
    import pygame
    if not all((SOUND_DIR / z[5]).exists() for z in ZONES.values()):
        from generate_sounds import generate
        generate()
    pygame.mixer.pre_init(44100, -16, 2, 256)   # small buffer = low latency
    pygame.mixer.init()
    pygame.mixer.set_num_channels(32)
    return {name: pygame.mixer.Sound(str(SOUND_DIR / z[5])) for name, z in ZONES.items()}


def draw(frame, flashes, wrongs, now, active, hud, hint, visible=None):
    h, w = frame.shape[:2]
    over = frame.copy()
    for name, (x1, y1, x2, y2, col, _) in ZONES.items():
        if visible is not None and name not in visible:
            continue
        p1, p2 = (int(x1 * w), int(y1 * h)), (int(x2 * w), int(y2 * h))
        if now - wrongs.get(name, -9) < 0.25:
            cv2.rectangle(over, p1, p2, (0, 0, 255), -1)
        elif now - flashes.get(name, -9) < 0.12:
            cv2.rectangle(over, p1, p2, col, -1)
        elif name in active:
            cv2.rectangle(over, p1, p2, (255, 255, 255), -1)
    cv2.addWeighted(over, 0.45, frame, 0.55, 0, frame)
    for name, (x1, y1, x2, y2, col, _) in ZONES.items():
        if visible is not None and name not in visible:
            continue
        p1, p2 = (int(x1 * w), int(y1 * h)), (int(x2 * w), int(y2 * h))
        cv2.rectangle(frame, p1, p2, (255, 255, 255) if name in active else col, 5 if name in active else 2)
        cv2.putText(frame, name, (p1[0] + 6, p1[1] + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 2)
    for i, line in enumerate(hud):
        cv2.putText(frame, line, (10, 20 + 20 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
    if hint:
        cv2.putText(frame, hint, (10, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--patient", default="demo_patient")
    ap.add_argument("--camera", type=int, default=0)
    ap.add_argument("--guided", action="store_true", help="compatibility alias for --mode guided")
    ap.add_argument("--mode", choices=("free", "guided", "timed", "reaction"), default="free")
    ap.add_argument("--sensitivity", type=float, default=0.8, help="lower values require more deliberate gestures")
    ap.add_argument("--width", type=int, default=640)
    ap.add_argument("--height", type=int, default=480)
    args = ap.parse_args()

    if args.guided:
        args.mode = "guided"
    sounds = load_sounds()
    cfg = StrikeConfig().scaled(args.sensitivity)
    from tracker import HandTracker
    tracker = HandTracker()

    cam = Camera(args.camera, args.width, args.height, 60)
    if not cam.opened:
        raise SystemExit("Could not open the camera. Try --camera 1, and check camera permissions.")

    cv2.namedWindow(WIN)
    rec = SessionRecorder(args.patient, args.mode, args.mode != "free")
    target_mode = TargetMode(rec, args.mode) if args.mode != "free" else None
    flashes, wrongs, closed_anchor = {}, {}, {}
    muted, debug = False, False
    last_v, total, good, started, last_seq, fps, last_t = 0.0, 0, 0, time.perf_counter(), -1, 0.0, None
    note, note_t = "", 0.0

    while True:
        frame, t, seq = cam.read()
        if frame is not None and seq != last_seq:
            last_seq = seq
            if last_t:
                fps = 0.9 * fps + 0.1 / max(t - last_t, 1e-3)
            last_t = t
            frame = cv2.flip(frame, 1)

            for p in tracker.update(frame):
                rec.add_position(p.label, t, p.x, p.y)
                if p.gesture == "closed" and p.label not in closed_anchor:
                    closed_anchor[p.label] = (t, p.x, p.y)

                col = SRC_COLOR[p.source]
                cv2.circle(frame, (p.px, p.py), 9, col, 2)
                cv2.putText(frame, f"{p.label[0]}:palm {p.gesture}", (p.px + 12, p.py - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 1)

                if p.gesture_event:
                    start_t, start_x, start_y = closed_anchor.pop(p.label, (t, p.x, p.y))
                    travel = ((p.x - start_x) ** 2 + (p.y - start_y) ** 2) ** 0.5
                    velocity = travel / max(t - start_t, 1e-3)
                    strike = Strike(t, p.x, p.y, velocity, travel,
                                    [(start_t, start_y), (t, p.y)])
                    zone = zone_at(strike.x, strike.y, HIT_MARGIN)
                    verdict = target_mode.on_strike(zone, t) if target_mode else None
                    rec.add_hit(p.label, strike, zone, None if verdict is None else verdict == "correct")
                    total += 1
                    last_v = strike.velocity
                    good += (verdict == "correct") if target_mode else (zone is not None)
                    if zone:
                        flashes[zone] = t
                        if verdict == "wrong":
                            wrongs[zone] = t
                        if not muted:
                            ch = sounds[zone].play()
                            if ch:
                                ch.set_volume(velocity_to_volume(strike.velocity, cfg))
                    if verdict in ("wrong", "off") or (not target_mode and zone is None):
                        note, note_t = ("WRONG DRUM" if verdict == "wrong" else "MISSED THE DRUMS"), t

            if target_mode:
                if not target_mode.active:
                    target_mode.start(t)
                target_mode.tick(t)

            if debug:
                for a, b in tracker.debug:
                    cv2.line(frame, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), (120, 120, 120), 1)

            hud = [f"{args.patient}  {int(t - started)}s  hits {total}  fps {fps:.0f}",
                   f"accuracy {100 * good / total:.0f}%  ({good}/{total})" if total else "accuracy -",
                   f"last hit speed {last_v:.1f}" + ("  [muted]" if muted else "")]
            if target_mode:
                label = {"guided": "GUIDED", "timed": "TIMED", "reaction": "REACTION"}[args.mode]
                hud.append(f"{label}  score {target_mode.score}  active {len(target_mode.active)}")
            if t - note_t < 0.8:
                cv2.putText(frame, note, (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 3)
            draw(frame, flashes, wrongs, t, target_mode.active if target_mode else set(), hud,
                 getattr(tracker, "hint", "") or "Close fist, place palm over a drum, open hand | q finish",
                 target_mode.active if target_mode and args.mode == "reaction" else None)
            cv2.imshow(WIN, frame)

        k = cv2.waitKey(1) & 0xFF
        if k == ord("q") or cv2.getWindowProperty(WIN, cv2.WND_PROP_VISIBLE) < 1:
            break
        if k == ord("m"):
            muted = not muted
        if k == ord("d"):
            debug = not debug

    cam.release()
    cv2.destroyAllWindows()
    s = rec.summary()
    if s["total_hits"] > 0:
        path = save_session(s)
        print(f"Saved {path}")
        print("Metrics:", {k: v for k, v in s["metrics"].items() if v is not None})
        print("See it in the clinician view:  python dashboard.py --patient", args.patient)
    else:
        print("No hits recorded, nothing saved.")


if __name__ == "__main__":
    main()
