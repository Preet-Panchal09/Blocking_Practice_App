# Volleyball Middle Blocking Practice

A Python-served phone web app for practicing middle blocking. The browser uses your phone camera and screen; Python serves the app and will host drill logic, scoring, and future computer-vision endpoints.

## What This Requires

- Python 3.11+
- A phone with a modern browser
- Camera permission in the browser
- HTTPS when opening the app from your phone

Phone browsers usually block camera access on plain `http://192.168.x.x`. The easiest private setup is to run the app locally and expose it with an HTTPS tunnel such as `ngrok`, `cloudflared`, or Tailscale Funnel. It does not need to be publicly discoverable for normal development.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Then open:

- Computer: `http://localhost:8000`
- Phone, via HTTPS tunnel: tunnel URL pointing to `http://localhost:8000`

## Current Working Features

- Phone camera capture with an on-camera landmark and court-guide overlay
- MediaPipe pose landmark recognition through the FastAPI backend
- Timed standing-pose calibration and loaded-stance recognition
- Read, left-close, and right-close drill selection with cues and rep tracking
- Landscape iPhone camera controls with safe-area-aware responsive positioning
- Health, drill, calibration, and vision API endpoints

## Next Priorities

1. Improve image-recognition responsiveness and reduce frame-analysis latency.
2. Add reliable jump recognition using calibrated body movement over time.
3. Expand rep timing, consistency scoring, hand-position checks, and blocking feedback.

## Python-First Landmark Detection

The app keeps browser-required camera work in JavaScript and pose analysis in Python:

- `app/templates/index.html` provides the camera, landmark canvas, responsive controls, and drill selection.
- `app/static/app.js` captures frames, calls the vision API, draws landmarks, and manages calibration and drill interactions.
- `app/vision.py` runs the bundled MediaPipe pose landmarker and returns normalized tracked joints.
- `app/basepose.py` and `app/bodysignals.py` calibrate the athlete's standing pose and recognize a loaded stance.
- `app/drills.py` owns drill state, cue timing, and rep counts.

Planned volleyball-specific checks include:

- Ready stance: hips low, knees bent, feet wider than hips.
- Hands ready: wrists above elbows and in front of shoulders.
- Jump: hips and shoulders move upward quickly.
- Press: wrists cross above the net-line overlay.


