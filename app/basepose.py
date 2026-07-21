from dataclasses import dataclass, field
from statistics import median

from app.helperfunctions import average_y, get_if_visible, get_landmark_by_name


BASE_POSE_FIELDS = ("hip_y", "knee_y", "ankle_y", "wrist_y", "shoulder_y")

@dataclass
class BasePose:
    hip_y: float | None = None
    knee_y: float | None = None
    ankle_y: float | None = None
    wrist_y: float | None = None
    shoulder_y: float | None = None
    _samples: dict[str, list[float]] = field(
        default_factory=lambda: {name: [] for name in BASE_POSE_FIELDS},
        repr=False,
    )

    def reset(self) -> None:
        self.hip_y = None
        self.knee_y = None
        self.ankle_y = None
        self.wrist_y = None
        self.shoulder_y = None
        self._samples = {name: [] for name in BASE_POSE_FIELDS}

    @property
    def sample_count(self) -> int:
        return min((len(values) for values in self._samples.values()), default=0)

    def is_ready(self, minimum_samples: int) -> bool:
        return self.sample_count >= minimum_samples and self.get_base_pose() is not None

    def get_base_pose(self) -> dict | None:
        if (
            self.hip_y is None
            or self.knee_y is None
            or self.ankle_y is None
            or self.wrist_y is None
            or self.shoulder_y is None
        ):
            return None

        return {
            "hip_y": self.hip_y,
            "knee_y": self.knee_y,
            "ankle_y": self.ankle_y,
            "wrist_y": self.wrist_y,
            "shoulder_y": self.shoulder_y,
        }

    def calibrate_base_pose(self, landmarks: list[dict]) -> dict | None:
        left_hip = get_landmark_by_name(landmarks, "left_hip")
        right_hip = get_landmark_by_name(landmarks, "right_hip")
        left_knee = get_landmark_by_name(landmarks, "left_knee")
        right_knee = get_landmark_by_name(landmarks, "right_knee")
        left_ankle = get_landmark_by_name(landmarks, "left_ankle")
        right_ankle = get_landmark_by_name(landmarks, "right_ankle")
        left_wrist = get_landmark_by_name(landmarks, "left_wrist")
        right_wrist = get_landmark_by_name(landmarks, "right_wrist")
        left_shoulder = get_landmark_by_name(landmarks, "left_shoulder")
        right_shoulder = get_landmark_by_name(landmarks, "right_shoulder")

        current_pose = {
            "hip_y": average_y(landmarks, "left_hip", "right_hip")
            if get_if_visible(left_hip) and get_if_visible(right_hip)
            else None,
            "knee_y": average_y(landmarks, "left_knee", "right_knee")
            if get_if_visible(left_knee) and get_if_visible(right_knee)
            else None,
            "ankle_y": average_y(landmarks, "left_ankle", "right_ankle")
            if get_if_visible(left_ankle) and get_if_visible(right_ankle)
            else None,
            "wrist_y": average_y(landmarks, "left_wrist", "right_wrist")
            if get_if_visible(left_wrist) and get_if_visible(right_wrist)
            else None,
            "shoulder_y": average_y(landmarks, "left_shoulder", "right_shoulder")
            if get_if_visible(left_shoulder) and get_if_visible(right_shoulder)
            else None,
        }

        # A calibration sample is useful only when the complete reference pose
        # is visible. This prevents unrelated joints from coming from different
        # moments as the athlete moves in and out of frame.
        if any(value is None for value in current_pose.values()):
            return None

        for name, value in current_pose.items():
            self._samples[name].append(value)
            setattr(self, name, median(self._samples[name]))

        return self.get_base_pose()
