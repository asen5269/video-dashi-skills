import json
from pathlib import Path

from scripts.analyze_video import classify_aspect_ratio, normalize_probe


def test_classify_aspect_ratio_vertical():
    assert classify_aspect_ratio(1080, 1920) == "9:16"


def test_classify_aspect_ratio_horizontal():
    assert classify_aspect_ratio(1920, 1080) == "16:9"


def test_classify_aspect_ratio_square():
    assert classify_aspect_ratio(1080, 1080) == "1:1"


def test_normalize_probe_reads_video_and_audio():
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "video_metadata.json"
    data = json.loads(fixture.read_text(encoding="utf-8"))
    result = normalize_probe(data)

    assert result["width"] == 720
    assert result["height"] == 1280
    assert result["aspect_ratio"] == "9:16"
    assert result["duration_seconds"] == 31.52
    assert result["fps"] == 30.0
    assert result["has_audio"] is True
