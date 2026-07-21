from dataclasses import dataclass
from app.basepose import BasePose
from app.helperfunctions import average_y, get_if_visible, get_landmark_by_name

@dataclass
class Bodysignal:
    hip_y: float | None
    knee_y: float | None
    ankle_y: float | None
    wrist_y: float | None
    shoulder_y: float | None

    @staticmethod
    def get_body_signal_from_landmarks(landmarks: list[dict]) -> "Bodysignal | None":
        if not (
            get_if_visible(get_landmark_by_name(landmarks, "left_hip"))
            and get_if_visible(get_landmark_by_name(landmarks, "right_hip"))
            and get_if_visible(get_landmark_by_name(landmarks, "left_knee"))
            and get_if_visible(get_landmark_by_name(landmarks, "right_knee"))
            and get_if_visible(get_landmark_by_name(landmarks, "left_ankle"))
            and get_if_visible(get_landmark_by_name(landmarks, "right_ankle"))
            and get_if_visible(get_landmark_by_name(landmarks, "left_wrist"))
            and get_if_visible(get_landmark_by_name(landmarks, "right_wrist"))
            and get_if_visible(get_landmark_by_name(landmarks, "left_shoulder"))
            and get_if_visible(get_landmark_by_name(landmarks, "right_shoulder"))
        ):
            return None

        return Bodysignal(
            hip_y=average_y(landmarks, "left_hip", "right_hip"),
            knee_y=average_y(landmarks, "left_knee", "right_knee"),
            ankle_y=average_y(landmarks, "left_ankle", "right_ankle"),
            wrist_y=average_y(landmarks, "left_wrist", "right_wrist"),
            shoulder_y=average_y(landmarks, "left_shoulder", "right_shoulder"),
        )
    
    @staticmethod
    def get_is_loaded(bodysignal: "Bodysignal | None", base_pose: BasePose) -> bool:
        if bodysignal is None:
            return False

        if (
            bodysignal.hip_y is None
            or bodysignal.shoulder_y is None
            or base_pose.hip_y is None
            or base_pose.shoulder_y is None
        ):
            return False
        
        return (
            bodysignal.hip_y - base_pose.hip_y > 0.05
            and bodysignal.shoulder_y - base_pose.shoulder_y > 0.05
        )