# AirCare

AirCare is a webcam rehabilitation game that turns hand exercises into virtual
drumming and gives care teams explainable movement trends.

The runnable application is in [`AirCare/`](AirCare/). It uses MediaPipe Hands,
OpenCV, NumPy, Pygame, Tkinter, and an optional Google AI Studio Gemini API.

## Run

```powershell
cd AirCare
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

The launcher provides a mode dropdown:

- **Free Play** — play any visible drum.
- **Guided** — one highlighted drum at a time.
- **Timed** — two targets are active for two seconds.
- **Reaction Test** — exactly two drums are visible; each successful hit is replaced.

The hit gesture is deliberate: close the fist, place the palm over a drum, then open
the hand. The palm position at the open-palm event determines the target.

## Reports and Gemini summaries

The launcher can open the clinician dashboard and summarize all saved patients.
The optional summary uses Google AI Studio Gemini to produce two general sentences
and approximately three sentences per patient from aggregate session metrics, trends,
baselines, and flags. It does not send webcam video, raw images, or landmarks.

Configure the key in the shell instead of committing it:

```powershell
$env:GOOGLE_API_KEY = "your-replacement-key"
$env:AIRCARE_GEMINI_MODEL = "gemini-3.8-flash"
```

Without a key, AirCare uses a local summary template. Each click of **Summarize**
with a configured key sends a fresh request to Gemini, so the result is
AI-generated and may consume Google AI Studio quota or credits.

## Direct commands

```powershell
cd AirCare
python main.py --patient alex --mode free
python main.py --patient alex --mode guided
python main.py --patient alex --mode timed
python main.py --patient alex --mode reaction
python dashboard.py --patient alex
python dashboard.py --export report.html --patient alex
python -m unittest discover -s tests
```

AirCare is a screening and engagement aid, not a diagnostic device. Measurements are
relative to the camera setup and should be compared with the same patient over time.
