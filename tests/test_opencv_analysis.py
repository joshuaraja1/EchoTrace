from pathlib import Path

import cv2
import numpy as np

from echotrace_video.opencv_analysis import analyze_frames


def test_opencv_frame_analysis_measures_motion(tmp_path: Path):
    first = np.zeros((40, 50, 3), dtype=np.uint8)
    second = first.copy()
    second[:, 25:] = 255
    first_path = tmp_path / "first.jpg"
    second_path = tmp_path / "second.jpg"
    assert cv2.imwrite(str(first_path), first)
    assert cv2.imwrite(str(second_path), second)

    results = analyze_frames([first_path, second_path])
    assert results[0]["width"] == 50
    assert results[0]["motion_score"] == 0
    assert results[1]["motion_score"] > 0.45
