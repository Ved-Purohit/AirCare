# AirCare

AirCare is a webcam-based rehabilitation game that turns hand exercises into virtual
drumming. It records movement trends and gives care teams an explainable view of
potential changes over time.

```
webcam -> MediaPipe hand tracker -> palm gesture hit detector -> drum sounds
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
python app.py                                  # recommended launcher
python main.py --patient alex                 # direct game
python main.py --patient alex --guided         # guided rehab: a drum lights up, hit that one
python dashboard.py                            # clinician view at http://127.0.0.1:8000
python dashboard.py --export report.html       # static file you can send or screenshot
```

Keys in the game: `q` finish and save, `g` toggle guided mode, `d` debug view, `m` mute.

`--guided` and pressing `g` are the same thing: `--guided` starts with it on, `g` switches it on or off while playing. Sessions are compared with earlier sessions of the same type, so for clean dashboard trends start each session in one mode.

## What gets tracked

In hands mode each hand is tracked through a palm gesture state:

1. **closed fist**: establishes the intentional starting state.
2. **palm**: the palm center is tracked as the hit location.
3. **open palm**: spreading all four fingers creates one hit event.

AirCare no longer uses stick or color-object tracking. A hit is accepted only when a
closed fist becomes an open palm while the palm is over a drum zone.

## Drums and hits

Six drums are shown in two rows: kick, snare, tom, cymbal, hi-hat, and cowbell.
The palm position at the open-palm event determines which drum plays.

## Accuracy (every mode)

Every strike is judged and the live HUD shows the running accuracy:
- free play: an open-palm event counts as accurate if it lands on a drum, and a miss if it lands in empty space
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

If `GOOGLE_API_KEY` or `GEMINI_API_KEY` is set, Google AI Studio Gemini writes a
plain-language briefing from aggregated dashboard metrics only. We use it to help
clinicians quickly understand what changed and why it may matter. No webcam video,
raw images, or hand landmarks are sent. Without a key, AirCare uses a built-in
template and works offline. Set `AIRCARE_GEMINI_MODEL` to change the model.

## Files

| File | What it does |
|---|---|
| `main.py` | live game: tracking, sound, overlay, guided mode, accuracy, saves the session |
| `camera.py` | threaded camera that always returns the newest frame (lower latency) |
| `tracker.py` | MediaPipe palm tracking and closed-fist/open-palm gesture recognition |
| `strike.py` | legacy movement tests and velocity-to-volume mapping |
| `metrics.py` | session recorder and movement metrics |
| `analytics.py` | personal baseline, flags, trend detection, explanations |
| `summary.py` | Gemini or offline plain-language briefing from aggregate metrics |
| `dashboard.py` | clinician view, no dependencies, inline SVG charts |
| `seed_demo.py` | synthetic patient history for demos |
| `generate_sounds.py` | synthesises the drum samples (also auto-runs on first start) |
| `tests/` | `python -m unittest discover -s tests` |

## Tuning

- Hits missed: raise `--sensitivity` (try 1.3 to 2.0) or improve lighting.
- Phantom hits: lower `--sensitivity`, or raise `v_min` / `min_travel` in `config.py`.
- Palm gesture not found: show the whole hand, close the fist fully, then spread all four fingers clearly.
- Wrong drum fires: the hit spot is where the stroke stops; stop your hand over the drum, or enlarge `HIT_MARGIN` in `config.py`.
- Latency: keep 640x480, close other camera apps, use wired headphones.
- Camera not found: `--camera 1`.
- Install trouble with mediapipe: use Python 3.10 or 3.11.

## Limits (say these out loud to judges)

- A screening and engagement aid, not a diagnostic device. Flags prompt a human to look.
- Measurements are relative to the camera frame. Compare a patient only with themselves, camera in a similar spot.
- Palm gesture recognition depends on clear hand visibility, lighting, and camera angle.
- The demo patients are synthetic (labelled in the dashboard). No clinical validation has been done.
- Video stays on the device; only summary numbers are stored.
