AirCare
Engaging Rehabilitation with Early Movement Insights
AirCare transforms a webcam into an accessible air-drumming rehabilitation game. Patients play six virtual instruments using hand movements, making rehabilitation more enjoyable while generating movement metrics clinicians can monitor over time.

Goal: Encourage consistent rehabilitation and help care teams notice potential movement changes earlier—not diagnose medical conditions.

The Problem
Upper-limb rehabilitation can be repetitive, difficult to maintain at home, and hard to monitor between appointments. Changes in movement speed, range, coordination, rhythm, reaction time, or participation may go unnoticed.

AirCare combines an engaging activity with repeatable movement tracking to make these changes easier to identify and discuss.

Who Is It For?
Clinicians: Occupational and physical therapists, rehabilitation assistants, and neurological care teams.
Patients: People recovering from stroke or neurological injury, or experiencing weakness, stiffness, or coordination difficulties.
Caregivers: Families and senior-care teams supporting rehabilitation.
Digital-health innovators: Developers exploring accessible, camera-based health technology.
How It Works
Patients use their hands in front of a webcam to play virtual kick, snare, tom, cymbal, hi-hat, and cowbell instruments.

Free play: Create rhythms and strike any instrument.
Guided mode: Follow highlighted targets to measure accuracy and reaction time.
Real-time feedback: Faster movements produce louder sounds.
Flexible gestures: Taps, swipes, and sharp direction changes can trigger hits.
MediaPipe Hands tracks hand landmarks, OpenCV processes camera input and visuals, and Pygame plays synthesized instrument sounds.

Key Features
Engaging rehabilitation: Makes repetitive exercises feel like making music.
Accessible hardware: Requires only a computer and webcam.
Movement analytics: Measures amplitude, reach, speed, smoothness, rhythm variability, left-right asymmetry, accuracy, reaction time, and engagement.
Personal baselines: Compares patients with their own previous sessions.
Explainable alerts: Describes changes in plain language rather than presenting opaque risk scores.
Trend monitoring: Highlights gradual changes that may be missed in individual sessions.
From Movement to Insight

Observed change	Possible factor to investigate
Smaller movements	Fatigue or reduced range of motion
Slower movements	Weakness or stiffness
Reduced smoothness	Changes in motor control
Irregular rhythm	Coordination or attention changes
Greater left-right difference	Possible movement asymmetry
Slower guided responses	Fatigue or attention changes
Fewer sessions	Reduced engagement or adherence
These signals are not diagnoses. They provide clinicians with evidence to review and discuss.

Clinician Dashboard
A lightweight Python HTTP server displays session summaries, movement trends, personal baselines, and explanations for flagged changes. Reports can also be exported as standalone HTML.

An optional Google AI Studio Gemini integration generates clinician briefings from aggregate metrics. Google AI Studio offers a free API tier subject to current quotas and terms. No webcam video or raw image frames are sent to the model; an offline template is available without an API key.

Why AirCare Matters
AirCare combines three essential elements:

Adherence: Music-based gameplay encourages patients to participate.
Measurement: Movement data is collected during the activity.
Actionability: Explainable trends help care teams decide when to investigate further.
This approach aims to make rehabilitation more engaging while improving visibility between appointments.

Expected Impact
Near-term

More enjoyable home- and facility-based exercise.
Easier check-ins between appointments.
Earlier visibility into movement changes.
Better communication between patients, caregivers, and clinicians.
Long-term

Personalized rehabilitation support.
Integration with clinical records.
Improved performance across cameras and environments.
Clinical validation and expansion to other exercises.
Limitations and Safety
AirCare is a prototype, not a clinically validated diagnostic device. Measurements depend on camera positioning, lighting, and hand visibility. The system does not directly measure physical force or true 3D depth.

Real-world deployment would require clinical validation, informed consent, privacy and security safeguards, data-retention policies, and regulatory review. Synthetic demo patients are not clinical evidence.

Intended use: A rehabilitation engagement and screening aid that helps care teams notice potential changes sooner.

Two-Minute Demo
Opening: “Rehabilitation can be repetitive, and early signs of decline may appear between appointments. AirCare turns a webcam into an air-drumming game that motivates patients to practice while giving care teams explainable movement trends.”

Demonstration:

Launch `python app.py`, choose a patient, and press **Start AirCare**.
Choose guided mode and hit the highlighted instruments.
Show how movement speed affects sound volume.
Demonstrate a sharp turn triggering a hit.
Switch to free play using g.
Press **Open Report** to launch the dashboard and highlight personal baselines and alert explanations.
Closing: “AirCare doesn't replace a therapist. It gives patients an activity they want to repeat and gives care teams a clearer reason to look closer.”

Setup

python seed_demo.py
python app.py
```

For a direct guided-session demo without the launcher:

```bash
python main.py --patient demo_patient --guided
python dashboard.py --patient demo_patient
Recommended setup: Position the webcam at chest height, approximately one metre away, with even lighting and an uncluttered background.

Technology Stack
Python, OpenCV, MediaPipe Hands, NumPy, Pygame, procedural WAV synthesis, the Python standard library, and optional Gemini API summarization.