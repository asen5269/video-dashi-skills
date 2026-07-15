import pytest

from scripts.resolve_reference_video import extension_from, resolve


def test_resolve_accepts_local_video_path(tmp_path):
    video = tmp_path / "uploaded.mp4"
    video.write_bytes(b"fake")

    result = resolve(str(video), tmp_path / "out")

    assert result["input_type"] == "local_video"
    assert result["video_path"] == str(video.resolve())
    assert result["parser_result"] is None


def test_extension_from_content_type():
    assert extension_from("https://example.com/video", "video/webm") == ".webm"
    assert extension_from("https://example.com/video", "video/mp4") == ".mp4"


def test_resolve_social_link_without_video_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "scripts.resolve_reference_video.parse_douyin",
        lambda text: {"videos": [], "images": ["https://example.com/a.jpg"]},
    )

    with pytest.raises(SystemExit, match="No video URL found"):
        resolve("https://v.douyin.com/test/", tmp_path)
