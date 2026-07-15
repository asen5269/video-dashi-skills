import numpy as np

from scripts.make_jimeng_joint_mannequin import JointSmoother, bgr


def test_bgr_converts_rgb_hex():
    assert bgr("#12abef") == (239, 171, 18)


def test_joint_smoother_blends_visible_joint():
    smoother = JointSmoother(alpha=0.5, threshold=0.25, hold_frames=2, track_hold=1)
    points = np.zeros((17, 2), np.float32)
    scores = np.ones(17, np.float32)
    box = np.array([0, 0, 100, 200], np.float32)
    smoother.update(1, points, scores, box, 0)
    moved = points.copy()
    moved[5] = (10, 20)
    state = smoother.update(1, moved, scores, box, 1)
    assert np.allclose(state["points"][5], (5, 10))


def test_joint_smoother_holds_temporarily_missing_joint():
    smoother = JointSmoother(alpha=1, threshold=0.25, hold_frames=2, track_hold=1)
    points = np.ones((17, 2), np.float32)
    scores = np.ones(17, np.float32)
    box = np.array([0, 0, 100, 200], np.float32)
    smoother.update(1, points, scores, box, 0)
    scores[5] = 0
    state = smoother.update(1, points * 9, scores, box, 1)
    assert np.allclose(state["points"][5], (1, 1))
    assert state["scores"][5] > 0
