# AirRhythm: Devpost write-up and demo plan

## Tagline
Rehab you actually want to do, and an early warning for the care team when movement starts to slip.

## Where to submit
- Theme: Healthcare Innovation and Well-being.
- Sponsor challenge: PointClickCare "Catch It Early". It asks for an AI-powered signal that spots a health risk sooner, aimed at the care team, with an explanation of why. Reduced mobility, strength and coordination are early warning signs for falls and decline in senior living, and the challenge says synthetic datasets are fine. Pitch it as upper-limb mobility early warning.
- Top 3 overall: the live demo is the strongest part, so lead with it.
- Skip FDM, School of Cities and Project KAZE; the idea doesn't fit them.

## Inspiration
Physical therapy is repetitive, and people stop doing it. Meanwhile the first signs of decline (smaller movements, slower strokes, one side lagging) are easy for a busy care team to miss between visits. A game people want to play can quietly capture exactly those signals.

## What it does
Play drums in mid-air with bare hands or any object, using just a webcam. Strike speed controls volume, like a real kit. A guided mode lights up drums to hit, which makes patients reach and reacts to how quickly they respond. Each session is turned into movement metrics: amplitude, reach, speed, smoothness, rhythm, left-right gap, accuracy and reaction time. A clinician dashboard compares every session with that patient's own baseline, flags meaningful changes, and says why each one matters.

## How we built it
- Computer vision: MediaPipe Hands, plus geometric stick-tip detection that works on any straight object (falling back to fingertip, then palm), and a click-to-calibrate colour tracker.
- Strike detection: a small state machine that fires when a quick downstroke slows, and uses where it stops as the hit spot. Almost no lockout, so fast rolls work (unit tested).
- Audio: pygame with a small buffer; volume comes from peak stroke speed.
- Analytics: personalised baselines, direction-aware thresholds per metric, and trend detection over the last 6 sessions. Every flag carries a plain-language explanation.
- Claude writes a short plain-language briefing for the therapist from aggregated numbers only; there is a template fallback so it works offline.
- Dashboard: dependency-free Python server with inline SVG charts.

## Challenges
Making any object work as a drumstick under changing light. Triggering on the stroke bottom instead of a raw speed threshold, which fixed the double-trigger and latency problems. Keeping the analytics explainable instead of a black box.

## Accomplishments
A live demo that works with a pen borrowed from a judge, and a dashboard that tells a therapist what changed and why, before it becomes an emergency.

## What we learned
Engagement is a clinical signal too. If someone stops playing, that is worth flagging.

## What's next
Clinical validation with occupational therapists, joint-level tracking with pose estimation, calibration against a known scale, and integration with care records.

## Built with
Python, OpenCV, MediaPipe, pygame, NumPy, Claude API.

## Honest limits
Screening and engagement aid, not diagnostic. Metrics are relative to the camera frame and meant to be compared with the patient's own history. Demo patients are synthetic and labelled as such.

## 2-minute demo script
1. (0:00) "Stroke and senior-care patients drop out of rehab, and decline between visits goes unnoticed." Start `python main.py --guided` and play with bare hands. Soft hits quiet, hard hits loud.
2. (0:30) Ask a judge for a pen. `python main.py --mode color`, click the tip, play. "Any object, no special hardware."
3. (0:50) Switch to the dashboard (`python dashboard.py --patient demo_patient`). "This is the care team's view. Eleven sessions of synthetic history."
4. (1:10) Point at the flags: left-right gap up 27 points against baseline, with the reason. "Caught from play, no clinic visit, with an explanation, not just an alert."
5. (1:40) Show `demo_stable` for contrast. Say the limits: screening aid, relative measures, synthetic demo data.
6. (1:55) Close: "Therapy people want to do, and an early warning for the people caring for them."

## Pre-demo checklist
- Run `python seed_demo.py` on demo day so the sessions are recent (otherwise the engagement flag appears after 7 days).
- Good front light, plain background, camera at chest height, about 1 metre back.
- Test sound output and keep a spare coloured object (bright tape on a pen works best).
- Have `python dashboard.py --export report.html` output ready as a backup.
