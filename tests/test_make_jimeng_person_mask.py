import argparse

import cv2
import numpy as np
import pytest

from scripts.make_jimeng_person_mask import clean_mask, largest_component, parse_rect


def test_largest_component_removes_smaller_regions():
    mask = np.zeros((20, 20), np.uint8)
    mask[2:12, 2:12] = 255
    mask[16:18, 16:18] = 255
    result = largest_component(mask)
    assert result[5, 5] == 255
    assert result[16, 16] == 0


def test_clean_mask_removes_isolated_noise():
    mask = np.zeros((31, 31), np.uint8)
    mask[8:24, 8:24] = 255
    mask[1, 1] = 255
    result = clean_mask(mask, 3, np.ones((3, 3), np.uint8))
    assert cv2.countNonZero(result) > 0
    assert result[1, 1] == 0


def test_parse_rect_rejects_out_of_bounds_rectangle():
    with pytest.raises(argparse.ArgumentTypeError):
        parse_rect("0.9,0.9,0.2,0.2")
