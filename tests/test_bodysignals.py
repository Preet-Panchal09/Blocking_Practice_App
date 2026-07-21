from app.basepose import BasePose
from app.bodysignals import Bodysignal

from conftest import make_landmarks


def test_unrelated_missing_joint_does_not_disable_jump_signal():
    landmarks = [
        landmark
        for landmark in make_landmarks(hip_y=0.47, shoulder_y=0.27)
        if "wrist" not in landmark["name"]
    ]
    signal = Bodysignal.get_body_signal_from_landmarks(landmarks)
    base_pose = BasePose(hip_y=0.50, shoulder_y=0.30)

    assert signal is not None
    assert signal.wrist_y is None
    assert Bodysignal.get_is_jumped(signal, base_pose)


def test_movement_threshold_scales_with_torso_height():
    base_pose = BasePose(hip_y=0.60, shoulder_y=0.40)
    below_threshold = Bodysignal(0.58, None, None, None, 0.38)
    above_threshold = Bodysignal(0.57, None, None, None, 0.37)

    assert not Bodysignal.get_is_jumped(below_threshold, base_pose)
    assert Bodysignal.get_is_jumped(above_threshold, base_pose)
