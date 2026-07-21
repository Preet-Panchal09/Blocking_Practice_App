from dataclasses import asdict
from time import monotonic

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.basepose import BasePose
from app.bodysignals import Bodysignal
from app.drills import DrillSession
from app.vision import analyze_frame

app = FastAPI(title="Blocking Practice")
drill_session = DrillSession()
base_pose = BasePose()
calibration_started_at: float | None = None
calibration_samples = 0

CALIBRATION_DELAY_SECONDS = 5
CALIBRATION_DURATION_SECONDS = 5

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health():
    return {"ok": True}


def calibration_snapshot() -> dict:
    if calibration_started_at is None:
        return {
            "active": False,
            "collecting": False,
            "samples": calibration_samples,
            "delay": CALIBRATION_DELAY_SECONDS,
            "duration": CALIBRATION_DURATION_SECONDS,
            "delayRemaining": 0,
            "timeRemaining": 0,
            "ready": base_pose.get_base_pose() is not None,
        }

    elapsed = monotonic() - calibration_started_at
    delay_remaining = max(0, CALIBRATION_DELAY_SECONDS - elapsed)
    collection_elapsed = max(0, elapsed - CALIBRATION_DELAY_SECONDS)
    time_remaining = max(0, CALIBRATION_DURATION_SECONDS - collection_elapsed)
    active = elapsed < CALIBRATION_DELAY_SECONDS + CALIBRATION_DURATION_SECONDS
    return {
        "active": active,
        "collecting": delay_remaining == 0 and active,
        "samples": calibration_samples,
        "delay": CALIBRATION_DELAY_SECONDS,
        "duration": CALIBRATION_DURATION_SECONDS,
        "delayRemaining": delay_remaining,
        "timeRemaining": time_remaining,
        "ready": base_pose.get_base_pose() is not None and not active,
    }


@app.post("/api/calibration/start")
async def start_calibration():
    global calibration_started_at, calibration_samples

    base_pose.reset()
    calibration_started_at = monotonic()
    calibration_samples = 0
    return calibration_snapshot()


@app.post("/api/drill/start")
async def start_drill(drill: str = Form("read")):
    return drill_session.start(drill)


@app.post("/api/drill/stop")
async def stop_drill():
    return drill_session.stop()


@app.get("/api/drill/tick")
async def drill_tick():
    return drill_session.tick()


@app.post("/api/vision/analyze")
async def analyze_camera_frame(frame: UploadFile = File(...)):
    global calibration_started_at, calibration_samples

    vision_result = analyze_frame(await frame.read())
    landmarks = vision_result["landmarks"]
    body_signal = Bodysignal.get_body_signal_from_landmarks(landmarks)
    calibration = calibration_snapshot()

    if calibration["collecting"]:
        base_pose.calibrate_base_pose(landmarks)
        if body_signal is not None:
            calibration_samples += 1

    if calibration_started_at is not None:
        elapsed = monotonic() - calibration_started_at
        if elapsed >= CALIBRATION_DELAY_SECONDS + CALIBRATION_DURATION_SECONDS:
            calibration_started_at = None

    calibration = calibration_snapshot()

    return {
        **vision_result,
        "bodySignal": asdict(body_signal) if body_signal else None,
        "basePose": base_pose.get_base_pose(),
        "isLoaded": Bodysignal.get_is_loaded(body_signal, base_pose),
        "calibration": calibration,
    }
