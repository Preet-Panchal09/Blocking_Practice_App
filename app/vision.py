from dataclasses import asdict, dataclass
from functools import lru_cache
from io import BytesIO
import logging
import os
from pathlib import Path
from threading import Lock

os.environ.setdefault(
    "MPLCONFIGDIR",
    str(Path(__file__).resolve().parent.parent / ".cache" / "matplotlib"),
)

import mediapipe as mp
import numpy as np
from PIL import Image, UnidentifiedImageError
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from app.helperfunctions import landmark_is_visible

logger = logging.getLogger(__name__)
MAX_FRAME_BYTES = 5 * 1024 * 1024

TRACKED_JOINTS = (
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
)

LANDMARK_INDEXES = {
    "left_shoulder": 11,
    "right_shoulder": 12,
    "left_elbow": 13,
    "right_elbow": 14,
    "left_wrist": 15,
    "right_wrist": 16,
    "left_hip": 23,
    "right_hip": 24,
    "left_knee": 25,
    "right_knee": 26,
    "left_ankle": 27,
    "right_ankle": 28,
}

MODEL_PATH = Path(__file__).with_name("pose_landmarker_full.task")
POSE_LANDMARKER_LOCK = Lock()


class FrameDecodeError(Exception):
    """The uploaded camera frame is missing or not a readable image."""


class VisionUnavailable(Exception):
    """The pose landmarker could not process a frame."""


@dataclass
class Landmark:
    name: str
    x: float
    y: float
    visibility: float | None = None


@lru_cache(maxsize=1)
def get_pose_landmarker() -> vision.PoseLandmarker:
    base_options = python.BaseOptions(model_asset_path=str(MODEL_PATH))
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.IMAGE,
        num_poses=1,
    )
    return vision.PoseLandmarker.create_from_options(options)


def image_from_jpeg(frame_bytes: bytes) -> mp.Image:
    if not frame_bytes:
        raise FrameDecodeError("Camera frame was empty")
    if len(frame_bytes) > MAX_FRAME_BYTES:
        raise FrameDecodeError("Camera frame is too large")

    try:
        image = Image.open(BytesIO(frame_bytes)).convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise FrameDecodeError("Camera frame could not be read") from exc

    pixels = np.ascontiguousarray(image)
    return mp.Image(image_format=mp.ImageFormat.SRGB, data=pixels)


def analyze_frame(frame_bytes: bytes) -> dict:
    """Run MediaPipe on a browser-captured frame and return normalized joints."""
    image = image_from_jpeg(frame_bytes)
    try:
        with POSE_LANDMARKER_LOCK:
            result = get_pose_landmarker().detect(image)
    except Exception as exc:
        logger.exception("Pose detection failed")
        raise VisionUnavailable("Pose detection is unavailable") from exc

    pose_landmarks = result.pose_landmarks[0] if result.pose_landmarks else []
    landmarks = []
    for name, index in LANDMARK_INDEXES.items():
        if not pose_landmarks or index >= len(pose_landmarks):
            continue
        point = pose_landmarks[index]
        if not landmark_is_visible(point.visibility):
            continue
        landmarks.append(
            Landmark(
                name=name,
                x=float(point.x),
                y=float(point.y),
                visibility=float(point.visibility),
            )
        )

    return {
        "landmarks": [asdict(landmark) for landmark in landmarks],
        "trackedJoints": TRACKED_JOINTS,
        "message": "Pose detected" if landmarks else "Step into frame",
    }
