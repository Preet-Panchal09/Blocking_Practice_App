from fastapi.testclient import TestClient

import app.main as main
from app.drills import AIRBORNE, LOADED
from conftest import make_landmarks


def vision_result(landmarks: list[dict]) -> dict:
    return {
        "landmarks": landmarks,
        "trackedJoints": tuple(landmark["name"] for landmark in landmarks),
        "message": "Pose detected",
    }


def calibrate(client: TestClient, monkeypatch) -> None:
    clock = {"now": 100.0}
    current_landmarks = {"value": make_landmarks(hip_y=0.55, shoulder_y=0.35)}
    monkeypatch.setattr(main, "monotonic", lambda: clock["now"])
    monkeypatch.setattr(
        main,
        "analyze_frame",
        lambda _frame: vision_result(current_landmarks["value"]),
    )

    client.post("/api/calibration/start")
    clock["now"] = 106.0
    for _ in range(main.CALIBRATION_MIN_SAMPLES):
        response = client.post("/api/vision/analyze", files={"frame": ("frame.jpg", b"x")})
        assert response.status_code == 200

    clock["now"] = 111.0
    response = client.post("/api/vision/analyze", files={"frame": ("frame.jpg", b"x")})
    assert response.json()["calibration"]["ready"] is True


def test_drill_requires_calibration_and_sessions_are_isolated(monkeypatch):
    first_client = TestClient(main.app)
    second_client = TestClient(main.app)

    assert first_client.post("/api/drill/start", data={"drill": "read"}).status_code == 409
    calibrate(first_client, monkeypatch)
    assert first_client.post("/api/drill/start", data={"drill": "read"}).status_code == 200
    assert second_client.post("/api/drill/start", data={"drill": "read"}).status_code == 409


def test_vision_events_advance_the_active_drill(monkeypatch):
    client = TestClient(main.app)
    calibrate(client, monkeypatch)
    assert client.post("/api/drill/start", data={"drill": "read"}).status_code == 200

    current_landmarks = {"value": make_landmarks(hip_y=0.58, shoulder_y=0.38)}
    monkeypatch.setattr(
        main,
        "analyze_frame",
        lambda _frame: vision_result(current_landmarks["value"]),
    )

    def analyze() -> dict:
        response = client.post("/api/vision/analyze", files={"frame": ("frame.jpg", b"x")})
        assert response.status_code == 200
        return response.json()

    analyze()
    assert analyze()["drill"]["phase"] == LOADED

    current_landmarks["value"] = make_landmarks(hip_y=0.52, shoulder_y=0.32)
    analyze()
    assert analyze()["drill"]["phase"] == AIRBORNE

    current_landmarks["value"] = make_landmarks(hip_y=0.55, shoulder_y=0.35)
    analyze()
    result = analyze()
    assert result["drill"]["reps"] == 1


def test_missing_pose_does_not_finish_a_rep(monkeypatch):
    client = TestClient(main.app)
    calibrate(client, monkeypatch)
    assert client.post("/api/drill/start", data={"drill": "left"}).status_code == 200

    current_landmarks = {"value": make_landmarks(hip_y=0.58, shoulder_y=0.38)}
    monkeypatch.setattr(
        main,
        "analyze_frame",
        lambda _frame: vision_result(current_landmarks["value"]),
    )

    def analyze() -> dict:
        response = client.post("/api/vision/analyze", files={"frame": ("frame.jpg", b"x")})
        assert response.status_code == 200
        return response.json()

    analyze()
    assert analyze()["drill"]["phase"] == LOADED
    current_landmarks["value"] = make_landmarks(hip_y=0.52, shoulder_y=0.32)
    analyze()
    assert analyze()["drill"]["phase"] == AIRBORNE

    current_landmarks["value"] = []
    analyze()
    result = analyze()
    assert result["landmarks"] == []
    assert result["isLoaded"] is False
    assert result["isJumped"] is False
    assert result["drill"]["phase"] == AIRBORNE
    assert result["drill"]["reps"] == 0


def test_home_page_and_static_assets_load():
    client = TestClient(main.app)
    page = client.get("/")
    assert page.status_code == 200
    assert "Start camera" in page.text
    assert "Calibrate" in page.text
    assert "Start drill" in page.text
    assert 'data-drill="read"' in page.text
    assert 'data-drill="left"' in page.text
    assert 'data-drill="right"' in page.text
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/styles.css").status_code == 200
    assert client.get("/health").json() == {"ok": True}


def test_assets_resolve_when_started_outside_the_project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    client = TestClient(main.app)
    assert client.get("/static/app.js").status_code == 200
    assert "Middle Block Lab" in client.get("/").text
