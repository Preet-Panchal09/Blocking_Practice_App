def make_landmarks(
    *,
    hip_y: float = 0.55,
    shoulder_y: float = 0.35,
    visibility: float = 0.99,
) -> list[dict]:
    joint_y = {
        "left_shoulder": shoulder_y,
        "right_shoulder": shoulder_y,
        "left_elbow": shoulder_y + 0.08,
        "right_elbow": shoulder_y + 0.08,
        "left_wrist": shoulder_y + 0.16,
        "right_wrist": shoulder_y + 0.16,
        "left_hip": hip_y,
        "right_hip": hip_y,
        "left_knee": hip_y + 0.18,
        "right_knee": hip_y + 0.18,
        "left_ankle": hip_y + 0.36,
        "right_ankle": hip_y + 0.36,
    }
    return [
        {"name": name, "x": 0.5, "y": y, "visibility": visibility}
        for name, y in joint_y.items()
    ]
