# AirCare

AirCare is a webcam-based air-drumming rehabilitation game. A patient plays six virtual instruments using only their hands. The application turns quick hand movements into drum sounds, records movement measurements, and gives clinicians an explainable view of changes over time.

It is designed around a simple idea:

> Make repetitive rehabilitation engaging, then use the activity itself to collect useful movement signals.

AirCare is a **screening and engagement aid**, not a diagnostic device. Its alerts are prompts for a clinician or caregiver to investigate.

---

## Table of contents

1. [What the application does](#what-the-application-does)
2. [System architecture](#system-architecture)
3. [User experience](#user-experience)
4. [Hand tracking](#hand-tracking)
5. [Strike detection](#strike-detection)
6. [Virtual instruments and sound](#virtual-instruments-and-sound)
7. [Free play and guided mode](#free-play-and-guided-mode)
8. [Metrics and analytics](#metrics-and-analytics)
9. [Clinician dashboard](#clinician-dashboard)
10. [Project structure](#project-structure)
11. [Installation](#installation)
12. [Running the project](#running-the-project)
13. [Desktop launcher](#desktop-launcher)
14. [Controls](#controls)
15. [Tuning and troubleshooting](#tuning-and-troubleshooting)
16. [Data storage and privacy](#data-storage-and-privacy)
17. [Testing](#testing)
18. [Known limitations](#known-limitations)
19. [Future improvements](#future-improvements)

---

## What the application does

The project has two connected parts:

### 1. Desktop launcher

`app.py` is the recommended entry point. It provides:

- AirCare branding and the supplied visual banner.
- Patient name input.
- Sensitivity input.
- Game-mode selection.
- A **Start AirCare** button that launches the live game in the selected mode.
- An **Open Report** button that launches the clinician dashboard in a browser.

The repository also includes a Windows build under `dist/AirCare/`. Run
`dist/AirCare/AirCare.exe` on Windows to use the packaged launcher without
installing Python. The packaged build keeps patient data beside the executable.

### 2. Live rehabilitation game

The live game:

- Opens a webcam.
- Detects up to two hands with MediaPipe Hands.
- Tracks the palm center rather than a fingertip.
- Requires a deliberate closed-fist to open-palm gesture for each hit.
- Draws six virtual drum zones over the camera image.
- Detects the transition from a closed fist to an open palm.
- Uses the palm position when the hand opens as the hit position.
- Plays an instrument sound when the final position is inside a drum zone.
- Makes louder sounds for faster movements.
- Records positions, hits, accuracy, timing, and movement metrics.

### 3. Clinician dashboard

The dashboard:

- Loads saved sessions for a patient.
- Separates guided and non-guided sessions when building comparisons.
- Builds a personal baseline from the patient’s earliest sessions.
- Compares the newest session against that baseline.
- Checks for gradual drift over recent sessions.
- Flags changes such as reduced speed, reduced amplitude, poorer smoothness, or increasing left-right imbalance.
- Explains each flag in plain language.
- Can use Gemini to write a short briefing from aggregate metrics only.
- Works offline with a built-in summary template when no API key is configured.
- The report includes **Export PDF / Image**, which opens the browser print dialog
  so the report can be saved as a PDF or sent to an image-capable printer.

---

## System architecture

```text
                         LIVE SESSION

 webcam
   |
   v
 camera.py
   |
   v
 tracker.py  --->  palm position and open/closed gesture for each hand
   |
   v
 main.py     --->  closed -> open palm + drum-zone check = strike
   |
   +------------------> zone_at(...) ---> instrument sound
   |
   v
 metrics.py  --->  session summary
   |
   v
 storage.py  --->  data/<patient>/<timestamp>.json
   |
   v
 analytics.py ---> personal baseline, trends, flags
   |
   +-----------> summary.py ---> optional Gemini briefing
   |
   v
 dashboard.py ---> clinician web view or static HTML report
```

### Main technologies

| Technology | Role |
|---|---|
| Python 3.9-3.12 | Application language |
| OpenCV | Webcam frames, mirroring, drawing, window interaction |
| MediaPipe Hands | Hand and landmark detection |
| NumPy | Position filtering, statistics, signal calculations |
| Pygame mixer | Low-latency instrument playback and volume control |
| Python `wave` module | Writing generated WAV samples |
| Python standard HTTP server | Dependency-free clinician dashboard |
| Google AI Studio Gemini API | Optional aggregate-metric briefing generation |

The application does not require a database server, frontend build system, or cloud backend.

---

## User experience

### Free play

In free play, the patient closes a fist, places the palm over a drum, and opens the
hand. AirCare checks the palm position at the opening moment. A sound plays only when
that palm is over a drum. Keeping the hand open does not repeatedly trigger hits.

### Timed

Two drums light at once. Each target remains active for two seconds, and the patient
earns a correct hit by opening their palm over an active drum before it expires.
Expired targets count as missed targets and are replaced.

### Reaction Test

Exactly two drums remain visible as active targets. When one is hit, it disappears
immediately and a new drum appears, creating a continuous reaction-and-accuracy test.

The launcher mode dropdown starts `free`, `guided`, `timed`, or `reaction` sessions.

### Guided mode

Guided mode randomly lights one drum at a time. The patient must hit the lit drum:

- Correct drum: recorded as correct.
- Different drum: recorded as a wrong-drum hit.
- Outside all drums: recorded as an off-drum miss.
- No response before the timeout: recorded as a missed target.

Guided mode also records reaction time from target appearance to the correct hit.

---

## Hand tracking

AirCare currently uses **hands only**. Stick detection and color calibration are not part of the active runtime.

### Palm gesture tracking

The tracker uses landmark 9, the palm/knuckle center, as the hit location. It checks
the tip, joint, and wrist geometry of the index, middle, ring, and pinky fingers:

- all four clearly extended: `open`;
- at most one extended: `closed`;
- anything between those states: keep the previous state.

A hit is emitted only on a `closed -> open` transition. This prevents an open hand,
small landmark jitter, or ordinary movement from producing repeated hits.

### Stabilization

MediaPipe landmarks naturally move by a few pixels even when the hand is still. The tracker applies adaptive smoothing:

- Smaller movements use stronger smoothing to reduce jitter.
- Larger movements use lighter smoothing to preserve responsiveness.

The tracker therefore behaves steadily at rest while remaining usable for quick drum movements.

### Hand identity

With two hands visible, hands are ordered by their horizontal position in the mirrored camera view and labeled `Left` and `Right`. Each hand has its own gesture state and movement history.

---

## Strike detection

`main.py` converts the tracker's deliberate gesture event into a strike.

For every frame, the tracker:

1. Smooths the palm position.
2. Classifies the hand as open, closed, or transitioning.
3. Remembers where the closed fist was placed.
4. Emits one event when the hand becomes an open palm.
5. Checks that palm position against the drum zones.

The old velocity and direction thresholds remain in `strike.py` for isolated regression
tests and volume mapping, but they no longer decide whether gameplay hits occur.

### Strike configuration

`StrikeConfig` in `config.py` controls:

| Setting | Meaning |
|---|---|
| `v_start` | Speed required to begin a movement |
| `v_min` | Minimum peak speed for a valid strike |
| `v_max` | Speed mapped to maximum volume |
| `decel_frac` | Fraction of peak speed at which the movement is considered stopped |
| `direction_change_deg` | Minimum velocity turn angle that can trigger a hit without a stop |
| `min_travel` | Minimum 2D movement distance |
| `cooldown_s` | Very short protection against duplicate triggers |
| `max_stroke_s` | Maximum lifetime of one movement |
| `pos_alpha` | Position smoothing factor |
| `vel_alpha` | Velocity smoothing factor |
| `track_gap_s` | Time after which tracking loss resets the detector |
| `end_lead_s` | Optional endpoint prediction amount |

The `--sensitivity` command-line option scales the start speed, minimum speed, maximum speed, and minimum travel thresholds together. A higher sensitivity makes slower and smaller movements count.

### Volume mapping

The strike’s peak speed is mapped to a volume between approximately `0.15` and `1.0`. Soft movements remain audible but quiet. Faster movements produce louder instruments.

---

## Virtual instruments and sound

The current layout has six instruments:

| Instrument | Position | Sound file |
|---|---|---|
| Kick | Top-left | `sounds/kick.wav` |
| Snare | Top-center | `sounds/snare.wav` |
| Tom | Top-right | `sounds/tom_mid.wav` |
| Cymbal | Bottom-left | `sounds/crash.wav` |
| Hi-hat | Bottom-center | `sounds/hihat.wav` |
| Cowbell | Bottom-right | `sounds/cowbell.wav` |

The cowbell is the intentionally distinctive extra instrument beyond the core kick, snare, tom, cymbal, and hi-hat set.

Instrument rectangles are configured in `config.py` through `ZONES`. Each zone contains:

```text
x1, y1, x2, y2, display_color, sound_filename
```

Coordinates are normalized from `0.0` to `1.0`, so the layout scales with the camera resolution.

### Sound generation

`generate_sounds.py` synthesizes local WAV files without downloading audio:

- Kick: decaying frequency sweep for a low drum impact.
- Snare: noise burst plus a short tonal body.
- Hi-hat: high-passed noise.
- Tom: decaying pitch sweep.
- Cymbal: metallic/high-frequency noise decay.
- Cowbell: two square-wave tones with decay.

The live application checks whether the configured sound files exist. If any are missing, it runs the generator automatically before loading Pygame sounds.

---

## Accuracy and session recording

Every strike is recorded, including misses.

For free play:

- A strike inside a drum is accurate.
- A strike outside all drums is an off-drum miss.

For guided mode:

- Only the currently lit drum is accurate.
- A different drum is a wrong-drum hit.
- Empty space is an off-drum miss.
- A target that times out is a missed target.

Each session stores:

- patient identifier,
- start time,
- duration,
- session mode,
- guided/free-play state,
- total hits,
- hits per minute,
- wrong-drum hits,
- off-drum hits,
- missed targets,
- hand positions,
- per-hand hit counts,
- peak and average movement speed,
- stroke amplitude,
- vertical and horizontal workspace,
- smoothness,
- rhythm variability,
- accuracy,
- guided reaction time.

---

## Movement metrics

`metrics.py` turns raw positions and strikes into summary values.

### Stroke amplitude

Average movement distance associated with recorded strikes, expressed as a percentage of the frame height.

### Workspace and reach

The range between the 5th and 95th position percentiles estimates how much of the frame the patient used:

- vertical workspace,
- horizontal workspace.

### Movement speed

Average and high-percentile strike speed. Lower values can indicate weakness, stiffness, fatigue, or reduced effort.

### Smoothness

The average speed divided by peak speed across a stroke. A lower ratio usually means the movement has more irregular changes or multiple small speed peaks.

### Rhythm variability

The coefficient of variation of intervals between strikes. Higher variability indicates less consistent timing.

### Left-right asymmetry

When both hands have enough hits, the recorder calculates the relative difference between left and right:

- speed gap,
- amplitude gap.

### Accuracy and reaction time

Guided sessions additionally include target accuracy and the average reaction time for successful targets.

---

## Baseline analytics

`analytics.py` is intentionally explainable rather than a black-box model.

### Personal baseline

The baseline is calculated from the patient’s earliest sessions of the same guided/non-guided type. The median is used so one unusually good or bad session has less influence.

At least two baseline sessions are needed before meaningful comparisons are made.

### Latest-session comparison

The newest session is compared with the patient’s baseline. Each metric has:

- a direction of improvement,
- a watch threshold,
- an alert threshold,
- a plain-language explanation.

Examples:

- A lower stroke amplitude can indicate reduced range of motion.
- A lower movement speed can accompany weakness or fatigue.
- A lower smoothness score can indicate jerkier control or tremor.
- A larger left-right gap can suggest a one-sided problem.
- Lower target accuracy can reflect coordination, vision, or attention changes.

### Trend detection

The latest session does not need to cross an alert threshold to be useful. The analyzer also fits a simple trend over the most recent sessions. A gradual negative trend can receive a watch flag before a large single-session decline appears.

### Engagement

If there has been no session for at least seven days, the dashboard adds an engagement watch flag. This is useful because stopping the activity can itself be an early signal that a patient needs support.

### Status values

The dashboard can report:

- `no_data`
- `building_baseline`
- `ok`
- `watch`
- `alert`

---

## Clinician dashboard

The dashboard is a small Python HTTP server with inline HTML, CSS, and SVG charts. It does not need React, Node, or a separate web server.

It shows:

- patient identity,
- number of sessions,
- current status,
- latest session summary,
- metric cards,
- baseline values,
- recent metric series,
- watch and alert explanations,
- session history,
- synthetic-data labeling where applicable.

Start the dashboard:

```bash
python dashboard.py
```

## Desktop launcher

The launcher is a small Tkinter application included in the repository. It does not package AirCare into an `.exe`; it runs the Python game and dashboard using the active Python interpreter.

The launcher flow is:

```text
app.py
  -> Start AirCare
       -> main.py
       -> free play or guided mode
       -> q saves the session
  -> Open Report
       -> dashboard.py
       -> browser clinician report
```

If the image does not load, the launcher still works and displays a text fallback title. The supplied banner is stored at `assets/aircare_banner.png`.

Open a specific patient:

```bash
python dashboard.py --patient alex
```

Use a different port:

```bash
python dashboard.py --port 8080
```

Export a static report:

```bash
python dashboard.py --patient alex --export report.html
```

The exported HTML can be sent or opened without running the dashboard server.

---

## Optional Gemini briefing with Google AI Studio

`summary.py` can ask Google Gemini to write a short clinician-facing briefing. Google AI Studio provides a free API tier subject to Google’s current quotas and terms. The app does not require the API: the built-in summary template remains available offline.

Only aggregate analysis data is sent:

- metric labels,
- baseline values,
- latest values,
- severities,
- explanations.

The application does not send:

- webcam frames,
- images,
- video,
- raw hand landmarks.

Create a Gemini API key in Google AI Studio, then configure it with:

```bash
set GOOGLE_API_KEY=your_key_here
set AIRCARE_GEMINI_MODEL=gemini-3.5-flash-lite
```

On macOS/Linux:

```bash
export GOOGLE_API_KEY=your_key_here
export AIRCARE_GEMINI_MODEL=gemini-3.5-flash-lite
```

If the key is not present, AirCare uses its local template and continues to work offline.

---

## Project structure

| File | Responsibility |
|---|---|
| `app.py` | Tkinter desktop launcher with Start and Report buttons |
| `main.py` | Live game loop, webcam display, zone rendering, input controls, sound playback, session save |
| `camera.py` | Threaded camera reader that keeps the newest frame to reduce latency |
| `tracker.py` | MediaPipe hand detection, palm gesture classification, adaptive palm smoothing |
| `strike.py` | Legacy movement tests and speed-to-volume mapping |
| `config.py` | Strike thresholds, instrument zones, audio filenames, hit margin |
| `metrics.py` | Raw position recording, hit recording, per-hand and session metrics |
| `storage.py` | JSON session persistence and patient listing |
| `analytics.py` | Personal baselines, thresholds, trends, engagement checks, explanations |
| `summary.py` | Built-in briefing and optional Gemini briefing |
| `dashboard.py` | Local clinician dashboard and static report export |
| `generate_sounds.py` | Procedural WAV sample generation |
| `seed_demo.py` | Synthetic patient history generation |
| `sounds/` | Generated WAV instrument samples |
| `data/` | Saved patient session JSON files |
| `tests/` | Unit tests for tracking, strikes, metrics, analytics, and zones |
| `requirements.txt` | Python dependencies |

---

## Installation

### Requirements

- Python 3.9-3.12
- A working webcam
- Speakers or headphones
- Windows, macOS, or Linux

MediaPipe is most reliable with Python 3.10 or 3.11 if installation problems occur.

### Windows

From PowerShell:

```powershell
cd D:\Hackathon\files\aircare
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell blocks activation, run the virtual-environment Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### macOS/Linux

```bash
cd aircare
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On macOS, allow camera access for the terminal or Python process when prompted.

---

## Running the project

### Recommended: open the AirCare app

```bash
python app.py
```

Use **Start AirCare** to enter the game and **Open Report** to open the dashboard. The launcher passes the selected patient, sensitivity, and guided-mode settings to the existing game process.

### Start a normal session

```bash
python main.py --patient alex
```

The direct command remains available for development and debugging. Most users should start with `python app.py`.

### Start guided rehabilitation

```bash
python main.py --patient alex --guided
```

### Make smaller/slower movements count

```bash
python main.py --patient alex --sensitivity 1.6
```

### Use another camera

```bash
python main.py --patient alex --camera 1
```

### Change capture resolution

```bash
python main.py --width 640 --height 480
```

### Create synthetic dashboard data

```bash
python seed_demo.py
python dashboard.py
```

The seeded patients are synthetic and must not be interpreted as clinical records.

---

## Controls

| Key | Action |
|---|---|
| `q` | Finish the session and save it |
| `g` | Toggle guided mode |
| `d` | Toggle tracking debug lines |
| `m` | Mute or unmute instrument sounds |

Closing the OpenCV window also ends the session.

---

## Tuning and troubleshooting

### The palm gesture is not detected

- Show the whole hand, not just the fingertips.
- Close the fist fully before opening it.
- Spread all four fingers clearly when opening.
- Keep the whole hand inside the camera frame.
- Use front lighting instead of strong backlighting.
- Avoid a busy background.
- Make sure the camera is not being used by another application.

### The point jitters

The tracker already applies adaptive smoothing. If jitter remains:

- improve lighting,
- move the camera farther away,
- use 640x480,
- keep the hand at a moderate distance from the lens,
- avoid motion blur.

### Palm hits are missed

Keep the palm inside the intended zone while opening. If detection is unreliable,
improve lighting, move farther from the camera, and make the fist-to-palm change
clearly. Do not repeatedly open and close during one intended hit.

### The wrong drum plays

The palm position when the hand opens determines the hit. Keep the palm inside the
intended zone. To make zones more forgiving, increase:

```python
HIT_MARGIN = 0.03
```

You can also edit the rectangles in `ZONES`.

### Audio is delayed

- Close other audio-heavy applications.
- Use wired headphones if possible.
- Keep the camera at 640x480.
- Avoid running multiple camera or dashboard processes.

### The camera cannot open

Try another camera index:

```bash
python main.py --camera 1
```

Also check operating-system camera permissions.

### The dashboard has no useful flags

The analyzer needs history. Run:

```bash
python seed_demo.py
```

or complete at least two comparable sessions for a patient. Guided and free-play sessions are analyzed separately when enough matching history exists.

---

## Data storage and privacy

Sessions are stored locally as JSON:

```text
data/
└── <patient>/
    └── <timestamp>.json
```

The local session file contains summary numbers and recorded movement-derived data. Video is not saved.

Patient names are sanitized before being used as directory names. The application has no built-in account system, encryption, or network database.

For a real deployment, add appropriate access control, encryption, retention policies, consent handling, and health-data compliance review.

---

## Testing

Run all tests:

```bash
python -m unittest discover -s tests
```

The test suite covers:

- legacy strike state-machine behavior,
- one movement producing expected legacy strike events,
- endpoint hit positions,
- sensitivity and velocity-to-volume behavior,
- tracking loss resets,
- closed-fist/open-palm gesture classification,
- zone boundaries and hit margins,
- session metrics,
- personal baselines,
- trend flags,
- engagement flags.

Compile-check the main modules:

```bash
python -m py_compile config.py tracker.py strike.py main.py metrics.py analytics.py dashboard.py app.py
```

---

## Known limitations

- This is not a medical diagnostic device.
- Measurements are relative to the camera frame, not physical centimeters.
- Sessions should use a similar camera position and distance for meaningful trends.
- MediaPipe can lose hands under occlusion, poor lighting, motion blur, or extreme angles.
- The system does not estimate depth.
- The current tracker follows the palm and recognizes an open-palm gesture, not a physical drumstick.
- Instrument zones are fixed rectangles rather than 3D surfaces.
- Sound intensity is based on tracked movement speed, not measured physical force.
- Synthetic demo patients are not real clinical data.
- No clinical validation has been performed.

---

## Future improvements

Potential next steps include:

- per-user camera calibration,
- depth-aware or 3D hand tracking,
- better identity preservation when hands cross,
- confidence-aware strike rejection,
- configurable instrument layouts,
- patient-specific sensitivity calibration,
- more realistic synthesized instrument samples,
- session pause/resume,
- clinician annotations,
- encrypted local storage,
- authenticated dashboard access,
- clinical validation with occupational and physical therapists.

---

## Quick start

For someone joining the project, the shortest path to understanding it is:

```bash
cd aircare
python -m venv .venv
python -m pip install -r requirements.txt
python seed_demo.py
python main.py --patient alex
```

Then open another terminal and run:

```bash
python dashboard.py --patient alex
```

Start with `main.py` to understand the live loop, then read `tracker.py`, `metrics.py`,
`analytics.py`, and `dashboard.py` in that order. The data path is:

```text
camera frame
  -> palm point and gesture
  -> open-palm event
  -> drum-zone hit
  -> session JSON
  -> baseline comparison
  -> dashboard explanation
```
