from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image
import pytest

import app.main as main
from app.vision import MAX_FRAME_BYTES, FrameDecodeError, analyze_frame, image_from_jpeg


def jpeg_bytes(color: tuple[int, int, int] = (24, 24, 24), size: tuple[int, int] = (160, 120)) -> bytes:
    image = Image.new("RGB", size, color)
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def test_unreadable_frames_are_rejected_before_pose_detection():
    with pytest.raises(FrameDecodeError):
        image_from_jpeg(b"")
    with pytest.raises(FrameDecodeError):
        image_from_jpeg(b"not-a-jpeg")
    with pytest.raises(FrameDecodeError):
        image_from_jpeg(b"x" * (MAX_FRAME_BYTES + 1))


def test_invalid_upload_returns_400_without_dropping_the_session():
    client = TestClient(main.app)
    response = client.post(
        "/api/vision/analyze",
        files={"frame": ("frame.jpg", b"not-a-jpeg", "image/jpeg")},
    )
    assert response.status_code == 400
    assert "frame" in response.json()["detail"].lower()
    assert client.get("/api/drill/tick").status_code == 200


def test_blank_frame_asks_the_athlete_to_step_in():
    result = analyze_frame(jpeg_bytes())
    assert result["message"] == "Step into frame"
    assert result["landmarks"] == []
    assert "left_hip" in result["trackedJoints"]
    assert "right_shoulder" in result["trackedJoints"]

    client = TestClient(main.app)
    response = client.post(
        "/api/vision/analyze",
        files={"frame": ("frame.jpg", jpeg_bytes(), "image/jpeg")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Step into frame"
    assert body["landmarks"] == []
    assert body["isLoaded"] is False
    assert body["isJumped"] is False
    assert body["bodySignal"] is None
    assert body["drill"]["reps"] == 0
