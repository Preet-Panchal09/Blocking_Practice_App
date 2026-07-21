from dataclasses import dataclass
from app.basepose import BasePose
from app.helperfunctions import average_y, get_if_visible, get_landmark_by_name


MOVEMENT_THRESHOLD_TORSO_RATIO = 0.12
MIN_MOVEMENT_THRESHOLD = 0.015


@dataclass
class Bodysignal:
    hip_y: float | None
    knee_y: float | None
    ankle_y: float | None
    wrist_y: float | None
    shoulder_y: float | None

    @staticmethod
    def get_body_signal_from_landmarks(landmarks: list[dict]) -> "Bodysignal | None":
        values = {
            "hip_y": average_y(landmarks, "left_hip", "right_hip"),
            "knee_y": average_y(landmarks, "left_knee", "right_knee"),
            "ankle_y": average_y(landmarks, "left_ankle", "right_ankle"),
            "wrist_y": average_y(landmarks, "left_wrist", "right_wrist"),
            "shoulder_y": average_y(landmarks, "left_shoulder", "right_shoulder"),
        }

        if all(value is None for value in values.values()):
            return None

        return Bodysignal(**values)

    @staticmethod
    def movement_threshold(base_pose: BasePose) -> float | None:
        if base_pose.hip_y is None or base_pose.shoulder_y is None:
            return None

        torso_height = abs(base_pose.hip_y - base_pose.shoulder_y)
        return max(MIN_MOVEMENT_THRESHOLD, torso_height * MOVEMENT_THRESHOLD_TORSO_RATIO)

    @staticmethod
    def get_is_loaded(bodysignal: "Bodysignal | None", base_pose: BasePose) -> bool:
        if bodysignal is None:
            return False

        threshold = Bodysignal.movement_threshold(base_pose)
        if (
            bodysignal.hip_y is None
            or bodysignal.shoulder_y is None
            or threshold is None
        ):
            return False

        return (
            bodysignal.hip_y - base_pose.hip_y > threshold
            and bodysignal.shoulder_y - base_pose.shoulder_y > threshold
        )

    @staticmethod
    def get_is_jumped(bodysignal: "Bodysignal | None", base_pose: BasePose) -> bool:
        if bodysignal is None:
            return False

        threshold = Bodysignal.movement_threshold(base_pose)
        if (
            bodysignal.hip_y is None
            or bodysignal.shoulder_y is None
            or threshold is None
        ):
            return False

        return (
            bodysignal.hip_y - base_pose.hip_y < -threshold
            and bodysignal.shoulder_y - base_pose.shoulder_y < -threshold
        )
