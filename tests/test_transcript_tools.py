from scripts.clean_transcript import parse_transcript, render_srt, render_timeline
from scripts.transcribe_audio import format_srt_timestamp, format_timestamp


def test_transcribe_timestamp_formatting():
    assert format_timestamp(65.4321) == "01:05.432"
    assert format_srt_timestamp(65.4321) == "00:01:05,432"


def test_clean_transcript_applies_replacements_and_renders_outputs():
    lines = parse_transcript(
        "language=zh probability=1.00\n\n00:00.000-00:02.000 鸡毛散皮 的事\n",
        {"鸡毛散皮": "鸡毛蒜皮"},
    )

    assert len(lines) == 1
    assert lines[0].text == "鸡毛蒜皮 的事"
    assert '00:00.000-00:02.000 Speaker says: "鸡毛蒜皮 的事"' in render_timeline(lines, "Speaker")
    assert "00:00:00,000 --> 00:00:02,000" in render_srt(lines)
