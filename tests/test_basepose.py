from app.basepose import BasePose

from conftest import make_landmarks


def test_calibration_requires_complete_samples_and_uses_median():
    base_pose = BasePose()

    incomplete = [
        landmark
        for landmark in make_landmarks()
        if landmark["name"] != "left_wrist"
    ]
    assert base_pose.calibrate_base_pose(incomplete) is None
    assert base_pose.sample_count == 0

    for hip_y in [0.55, 0.56, 0.54, 0.55, 0.90]:
        base_pose.calibrate_base_pose(make_landmarks(hip_y=hip_y))

    assert base_pose.sample_count == 5
    assert base_pose.hip_y == 0.55
    assert base_pose.is_ready(5)
    assert not base_pose.is_ready(6)
