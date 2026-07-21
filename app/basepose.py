from dataclasses import dataclass
from app.helperfunctions import get_if_visible, get_landmark_by_name, average_y

@dataclass
class BasePose:
    hip_y: float | None = None
    knee_y: float | None = None
    ankle_y: float | None = None
    wrist_y: float | None = None
    shoulder_y: float | None = None

    def reset(self) -> None:
        self.hip_y = None
        self.knee_y = None
        self.ankle_y = None
        self.wrist_y = None
        self.shoulder_y = None

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
        current_wrist_y = None
        current_ankle_y = None
        current_hip_y = None
        current_knee_y = None
        current_shoulder_y = None
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

        if get_if_visible(left_hip) and get_if_visible(right_hip):
            current_hip_y = average_y(landmarks, "left_hip", "right_hip")
        if get_if_visible(left_knee) and get_if_visible(right_knee):
            current_knee_y = average_y(landmarks, "left_knee", "right_knee")
        if get_if_visible(left_ankle) and get_if_visible(right_ankle):
            current_ankle_y = average_y(landmarks, "left_ankle", "right_ankle")
        if get_if_visible(left_wrist) and get_if_visible(right_wrist):
            current_wrist_y = average_y(landmarks, "left_wrist", "right_wrist")
        if get_if_visible(left_shoulder) and get_if_visible(right_shoulder):
            current_shoulder_y = average_y(landmarks, "left_shoulder", "right_shoulder")

        if self.hip_y is None:
            self.hip_y = current_hip_y
        elif current_hip_y is not None:
            self.hip_y = (self.hip_y + current_hip_y)/2
        
        if self.ankle_y is None:
            self.ankle_y = current_ankle_y
        elif current_ankle_y is not None:
            self.ankle_y = (self.ankle_y + current_ankle_y)/2
        
        if self.knee_y is None:
            self.knee_y = current_knee_y
        elif current_knee_y is not None:
            self.knee_y = (self.knee_y + current_knee_y)/2
        
        if self.wrist_y is None:
            self.wrist_y = current_wrist_y
        elif current_wrist_y is not None:
            self.wrist_y = (self.wrist_y + current_wrist_y)/2
        
        if self.shoulder_y is None:
            self.shoulder_y = current_shoulder_y
        elif current_shoulder_y is not None:
            self.shoulder_y = (self.shoulder_y + current_shoulder_y)/2
        
        return self.get_base_pose()
