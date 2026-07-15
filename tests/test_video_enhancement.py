from scripts.check_video_quality import inspect_video
from scripts.enhance_video import ffmpeg_filter, resolve_backend


def test_ffmpeg_filter_preserves_scale_and_uses_profile():
    result = ffmpeg_filter("compressed", 2)

    assert "scale=iw*2:ih*2:flags=lanczos" in result
    assert "hqdn3d" in result
    assert "unsharp" in result


def test_ffmpeg_filter_game_profile_avoids_denoise():
    result = ffmpeg_filter("game", 2)

    assert "scale=iw*2:ih*2:flags=lanczos" in result
    assert "hqdn3d" not in result


def test_resolve_backend_auto_uses_realesrgan_when_available(monkeypatch):
    monkeypatch.setattr("scripts.enhance_video.find_executable", lambda *names: "realesrgan-ncnn-vulkan.exe")

    assert resolve_backend("auto") == "realesrgan"


def test_resolve_backend_auto_falls_back_to_ffmpeg(monkeypatch):
    monkeypatch.setattr("scripts.enhance_video.find_executable", lambda *names: None)

    assert resolve_backend("auto") == "ffmpeg"


def test_inspect_video_recommends_two_x_for_vertical_720p():
    probe = {
        "streams": [
            {
                "codec_type": "video",
                "width": 720,
                "height": 1280,
                "duration": "14.5",
                "avg_frame_rate": "30/1",
                "bit_rate": "900000",
            },
            {"codec_type": "audio"},
        ],
        "format": {"duration": "14.5", "bit_rate": "1000000"},
    }

    result = inspect_video(probe)

    assert result["recommended_scale"] == 2
    assert result["has_audio"] is True
