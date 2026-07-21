from dataclasses import asdict, dataclass
from functools import lru_cache
from io import BytesIO
import os
from pathlib import Path

os.environ.setdefault(
    "MPLCONFIGDIR",
    str(Path(__file__).resolve().parent.parent / ".cache" / "matplotlib"),
)

import mediapipe as mp
import numpy as np
from PIL import Image
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

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
    image = Image.open(BytesIO(frame_bytes)).convert("RGB")
    return mp.Image(image_format=mp.ImageFormat.SRGB, data=np.asarray(image))


def analyze_frame(frame_bytes: bytes) -> dict:
    """Run MediaPipe on a browser-captured frame and return normalized joints."""
    result = get_pose_landmarker().detect(image_from_jpeg(frame_bytes))
    pose_landmarks = result.pose_landmarks[0] if result.pose_landmarks else []

    landmarks = [
        Landmark(
            name=name,
            x=pose_landmarks[index].x,
            y=pose_landmarks[index].y,
            visibility=pose_landmarks[index].visibility,
        )
        for name, index in LANDMARK_INDEXES.items() if pose_landmarks
    ]

    return {
        "landmarks": [asdict(landmark) for landmark in landmarks],
        "trackedJoints": TRACKED_JOINTS,
        "message": "Pose detected" if landmarks else "Step into frame",
    }
