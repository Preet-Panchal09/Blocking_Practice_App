def get_landmark_by_name(landmarks: list[dict], name: str) -> dict | None:
    for landmark in landmarks:
        if landmark.get("name") == name:
            return landmark
    return None
    
def get_if_visible(landmark: dict | None) -> bool:
    minimum: float = 0.7
    if landmark is None:
        return False

    visibility = landmark.get("visibility")
    if visibility is None:
        return False
        
    return visibility >= minimum

def average_y(landmarks: list[dict], left_name: str, right_name: str) -> float | None:
    left_landmark = get_landmark_by_name(landmarks, left_name)
    right_landmark = get_landmark_by_name(landmarks, right_name)

    if not get_if_visible(left_landmark) or not get_if_visible(right_landmark):
        return None

    left_y = left_landmark.get("y")
    right_y = right_landmark.get("y")
    if left_y is None or right_y is None:
        return None

    return (left_y + right_y) / 2
