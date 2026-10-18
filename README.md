# AirRhythm

Air drumming for rehab. Play drums in mid-air with your bare hands, or any random object (pen, chopstick, rolled-up paper). The harder and faster you strike, the louder the drum. While you play, AirRhythm measures how you move and shows the care team early signs of decline.

```
webcam -> tracker (MediaPipe hands / colour objects) -> strike detector -> drum sounds (volume = speed)
                                         |
                                         +-> session metrics -> per-patient baseline -> flags + explanation -> clinician dashboard
```

## Setup (about 5 minutes)

Needs Python 3.9-3.12 and a webcam.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python seed_demo.py              # creates synthetic patient history for the dashboard demo
```

macOS: allow camera access for your terminal when prompted.

## Run it

```bash
python main.py --patient alex                  # hands: tracks stick tip, else fingertip, else palm
python main.py --patient alex --guided         # guided rehab: a drum lights up, hit that one
python main.py --mode color                    # coloured objects: click one to calibrate
python main.py --sensitivity 1.6               # slower/smaller movements count (rehab patients)
python main.py --no-stick                      # hands mode without stick detection
python dashboard.py                            # clinician view at http://127.0.0.1:8000
python dashboard.py --export report.html       # static file you can send or screenshot
```

Keys in the game: `q` finish and save, `g` toggle guided mode, `d` debug view, `m` mute.

`--guided` and pressing `g` are the same thing: `--guided` starts with it on, `g` switches it on or off while playing. Sessions are compared with earlier sessions of the same type, so for clean dashboard trends start each session in one mode.

## What gets tracked

In hands mode each hand is tracked at the first of these that works, and the label next to the dot shows which (for example `R:stick`):

1. **stick**: the far end of a straight object sticking out of your fist. Any stick, pen or chopstick; no colour needed. Once found, the stick is followed relative to your hand, so it stays smooth even if a frame misses it.
2. **finger**: the index fingertip, when the finger is extended.
3. **palm**: the middle knuckle, when the hand is a fist and no stick is seen.

Stick detection works best with a stick that contrasts with the background, held so most of it sticks out of the fist, with the camera seeing it from the side or front. Press `d` to see the line segments it is considering.

Colour mode tracks up to two objects, including two identical ones (click one, both are found). For a long thin object the tip is the top end; use `--tip bottom` or `--tip center` to change that. Putting bright tape on the tip is the most reliable.

## Drums and hits

Eight drums in two rows: crash, high tom, mid tom, ride (top); hi-hat, snare, floor tom, cowbell (bottom). They sit below the top fifth of the frame because hands track worst near the top edge. Edit `ZONES` in `config.py` to move them.

A hit is a quick downward movement that stops. The spot where it stops is the hit spot, and the drum under it plays, with volume from how fast the stroke was. There is no long lockout between hits, so rolls and fast patterns work. The limit is the camera: at 60 fps about 10 hits per second per hand, at 30 fps about 5 to 6. The game asks for 60 fps; the HUD shows what you actually get. Good front light helps cameras run at full speed.

## Accuracy (every mode)

Every strike is judged and the live HUD shows the running accuracy:
- free play and colour mode: a hit counts as accurate if it lands on a drum, and a miss if it lands in empty space
- guided mode: only the lit drum is right; hitting a different drum flashes red and counts as wrong, and landing off every drum counts as a miss

Accuracy, wrong-drum hits, off-drum hits and missed targets are saved with each session. If accuracy is low in free play, the tracking or the drum layout needs attention, not you.

## What the dashboard flags (and why)

Each session is compared with that patient's own baseline (median of their first 3 sessions of the same type). The dashboard shows what changed, by how much, and a plain-language reason a therapist can sanity-check.

| Metric | Why it matters |
|---|---|
| Stroke amplitude, horizontal reach | range of motion |
| Movement speed | weakness, stiffness, fatigue |
| Smoothness (mean/peak speed ratio) | motor control, tremor |
| Rhythm variability | coordination |
| Left-right speed and amplitude gap | one-sided deficits |
| Target accuracy, reaction time (guided) | coordination, attention |
| Days since last session | engagement |

It also catches slow drift over the last 6 sessions, so a gradual decline is flagged before it crosses the alert line.

If `ANTHROPIC_API_KEY` is set, the briefing at the top is written by Claude from aggregated numbers only (no video, no images). Without a key it uses a built-in template, so the demo works offline. Set `AIRRHYTHM_MODEL` to change the model.

## Files

| File | What it does |
|---|---|
| `main.py` | live game: tracking, sound, overlay, guided mode, accuracy, saves the session |
| `camera.py` | threaded camera that always returns the newest frame (lower latency) |
| `tracker.py` | stick-tip / fingertip / palm tracker and the colour tracker |
| `strike.py` | strike detection (fires on deceleration, per-hand cooldown) and velocity-to-volume |
| `metrics.py` | session recorder and movement metrics |
| `analytics.py` | personal baseline, flags, trend detection, explanations |
| `summary.py` | plain-language briefing (Claude or template) |
| `dashboard.py` | clinician view, no dependencies, inline SVG charts |
| `seed_demo.py` | synthetic patient history for demos |
| `generate_sounds.py` | synthesises the drum samples (also auto-runs on first start) |
| `tests/` | `python -m unittest discover -s tests` |

## Tuning

- Hits missed: raise `--sensitivity` (try 1.3 to 2.0) or improve lighting.
- Phantom hits: lower `--sensitivity`, or raise `v_min` / `min_travel` in `config.py`.
- Stick not found (label stays `finger` or `palm`): plain background, more of the stick sticking out of the fist, press `d` to see what it sees. Or use colour mode with tape on the tip.
- Wrong drum fires: the hit spot is where the stroke stops; stop your hand over the drum, or enlarge `HIT_MARGIN` in `config.py`.
- Latency: keep 640x480, close other camera apps, use wired headphones.
- Camera not found: `--camera 1`.
- Install trouble with mediapipe: use Python 3.10 or 3.11.

## Limits (say these out loud to judges)

- A screening and engagement aid, not a diagnostic device. Flags prompt a human to look.
- Measurements are relative to the camera frame. Compare a patient only with themselves, camera in a similar spot.
- Stick detection is geometry-based (straight edges next to the fist), so a cluttered background can fool it; the label and `d` view show when it is guessing.
- The demo patients are synthetic (labelled in the dashboard). No clinical validation has been done.
- Video stays on the device; only summary numbers are stored.
