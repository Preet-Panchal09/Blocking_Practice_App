from dataclasses import asdict
from pathlib import Path
from secrets import token_urlsafe
from time import monotonic

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool

from app.bodysignals import Bodysignal
from app.practice import PracticeState
from app.vision import FrameDecodeError, VisionUnavailable, analyze_frame

APP_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Blocking Practice")
practice_sessions: dict[str, PracticeState] = {}

CALIBRATION_DELAY_SECONDS = 5
CALIBRATION_DURATION_SECONDS = 5
CALIBRATION_MIN_SAMPLES = 10
SESSION_COOKIE = "blocking_practice_session"
SESSION_TTL_SECONDS = 12 * 60 * 60

app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
templates = Jinja2Templates(directory=APP_DIR / "templates")


@app.middleware("http")
async def practice_session_middleware(request: Request, call_next):
    now = monotonic()
    expired_ids = [
        session_id
        for session_id, state in practice_sessions.items()
        if now - state.last_seen_at > SESSION_TTL_SECONDS
    ]
    for session_id in expired_ids:
        practice_sessions.pop(session_id, None)

    session_id = request.cookies.get(SESSION_COOKIE)
    is_new_session = session_id not in practice_sessions
    if is_new_session:
        session_id = token_urlsafe(18)
        practice_sessions[session_id] = PracticeState()

    state = practice_sessions[session_id]
    state.last_seen_at = now
    request.state.practice = state

    response = await call_next(request)
    if is_new_session:
        response.set_cookie(
            SESSION_COOKIE,
            session_id,
            httponly=True,
            max_age=SESSION_TTL_SECONDS,
            samesite="lax",
            secure=request.url.scheme == "https",
        )
    return response


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/health")
async def health():
    return {"ok": True}


def finish_calibration_if_due(state: PracticeState) -> None:
    if state.calibration_started_at is None:
        return

    elapsed = monotonic() - state.calibration_started_at
    if elapsed < CALIBRATION_DELAY_SECONDS + CALIBRATION_DURATION_SECONDS:
        return

    state.calibration_started_at = None
    if state.base_pose.is_ready(CALIBRATION_MIN_SAMPLES):
        state.calibration_message = "Calibration ready"
    else:
        state.base_pose.reset()
        state.calibration_message = "Not enough clear frames — recalibrate"


def calibration_snapshot(state: PracticeState) -> dict:
    finish_calibration_if_due(state)
    if state.calibration_started_at is None:
        return {
            "active": False,
            "collecting": False,
            "samples": state.base_pose.sample_count,
            "minimumSamples": CALIBRATION_MIN_SAMPLES,
            "delay": CALIBRATION_DELAY_SECONDS,
            "duration": CALIBRATION_DURATION_SECONDS,
            "delayRemaining": 0,
            "timeRemaining": 0,
            "ready": state.base_pose.is_ready(CALIBRATION_MIN_SAMPLES),
            "message": state.calibration_message,
        }

    elapsed = monotonic() - state.calibration_started_at
    delay_remaining = max(0, CALIBRATION_DELAY_SECONDS - elapsed)
    collection_elapsed = max(0, elapsed - CALIBRATION_DELAY_SECONDS)
    time_remaining = max(0, CALIBRATION_DURATION_SECONDS - collection_elapsed)
    active = elapsed < CALIBRATION_DELAY_SECONDS + CALIBRATION_DURATION_SECONDS
    return {
        "active": active,
        "collecting": delay_remaining == 0 and active,
        "samples": state.base_pose.sample_count,
        "minimumSamples": CALIBRATION_MIN_SAMPLES,
        "delay": CALIBRATION_DELAY_SECONDS,
        "duration": CALIBRATION_DURATION_SECONDS,
        "delayRemaining": delay_remaining,
        "timeRemaining": time_remaining,
        "ready": False,
        "message": None,
    }


@app.post("/api/calibration/start")
async def start_calibration(request: Request):
    state: PracticeState = request.state.practice
    state.base_pose.reset()
    state.drill_session.stop()
    state.calibration_started_at = monotonic()
    state.calibration_message = None
    return calibration_snapshot(state)


@app.post("/api/drill/start")
async def start_drill(request: Request, drill: str = Form("read")):
    state: PracticeState = request.state.practice
    if not calibration_snapshot(state)["ready"]:
        raise HTTPException(status_code=409, detail="Calibrate before starting a drill")
    return state.drill_session.start(drill)


@app.post("/api/drill/stop")
async def stop_drill(request: Request):
    state: PracticeState = request.state.practice
    return state.drill_session.stop()


@app.get("/api/drill/tick")
async def drill_tick(request: Request):
    state: PracticeState = request.state.practice
    return state.drill_session.tick()


@app.post("/api/vision/analyze")
async def analyze_camera_frame(request: Request, frame: UploadFile = File(...)):
    state: PracticeState = request.state.practice
    frame_bytes = await frame.read()
    try:
        vision_result = await run_in_threadpool(analyze_frame, frame_bytes)
    except FrameDecodeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except VisionUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    landmarks = vision_result["landmarks"]
    body_signal = Bodysignal.get_body_signal_from_landmarks(landmarks)
    pose_seen = (
        body_signal is not None
        and body_signal.hip_y is not None
        and body_signal.shoulder_y is not None
    )
    calibration = calibration_snapshot(state)

    if calibration["collecting"]:
        state.base_pose.calibrate_base_pose(landmarks)

    calibration = calibration_snapshot(state)
    is_ready = calibration["ready"]
    is_loaded = is_ready and Bodysignal.get_is_loaded(body_signal, state.base_pose)
    is_jumped = is_ready and Bodysignal.get_is_jumped(body_signal, state.base_pose)
    drill_state = state.drill_session.update(
        is_loaded,
        is_jumped,
        pose_seen=pose_seen,
    )

    return {
        **vision_result,
        "bodySignal": asdict(body_signal) if body_signal else None,
        "basePose": state.base_pose.get_base_pose() if is_ready else None,
        "isLoaded": is_loaded,
        "isJumped": is_jumped,
        "drill": drill_state,
        "calibration": calibration,
    }
