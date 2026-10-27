import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

from scripts.build_prompt_pack import render_seedance_prompt, validate_values
from scripts.extract_storyboard import detect_cuts, probe_timestamps, select_frames
from scripts.lint_seedance_prompt import lint_prompt
from scripts.make_depth_map_video import timing_info
from scripts.resolve_reference_video import resolve

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def values(tmp_path):
    image = tmp_path / "reference.png"
    Image.new("RGB", (48, 64), "red").save(image)
    return {
        "confirmed": True, "reference_mode": "storyboard", "frame_order": "right to left",
        "duration": "4 seconds", "duration_seconds": 4, "aspect_ratio": "3:4", "audio_mode": "silent",
        "style": "natural", "replacement_target": "none", "speech": "no", "dialogue_timeline": "No speech.",
        "preserve_rules": "Preserve composition.", "change_rules": "None.", "negative_rules": "No extra objects.",
        "assets": [{"id": "image_1", "role": "storyboard", "path": str(image)}],
        "shots": [{"id": "S1", "start": 0, "end": 4, "prompt": "Use image_1; camera moves left."}],
    }


def test_image_input_does_not_invent_video_properties(tmp_path):
    image = tmp_path / "panels.png"
    Image.new("RGB", (400, 300)).save(image)
    result = resolve(str(image), tmp_path)
    assert result["input_type"] == "storyboard_image"
    assert result["width"] == 400
    assert result["duration"] is None
    assert result["audio"] == "unknown"
    assert "video_path" not in result


def test_short_shot_covered_and_source_timestamps_recorded():
    times = [index / 100 for index in range(400)]
    frames, shots = select_frames(times, 4, [1.0, 1.05], 6, 1)
    assert {frame["shot_id"] for frame in frames} == {1, 2, 3}
    assert any(1.0 <= frame["timestamp"] < 1.05 for frame in frames)
    assert [frame["timestamp"] for frame in frames] == sorted(frame["timestamp"] for frame in frames)
    assert all(times[frame["source_frame_index"]] == frame["timestamp"] for frame in frames)
    assert shots[1] == {"shot_id": 2, "start": 1, "end": 1.05}
    with pytest.raises(SystemExit, match="increase --max-frames"):
        select_frames(times, 4, [1.0, 1.05], 2, 1)


def test_final_values_and_custom_order(values):
    assert validate_values(values) == []
    prompt = render_seedance_prompt(values)
    assert lint_prompt(prompt, "no", "storyboard", "right to left", 4) == []
    assert "No product replacement is requested." in prompt


@pytest.mark.parametrize("change,expected", [
    ({"confirmed": False}, "confirmed=true"),
    ({"unresolved_decisions": "Which product?"}, "unresolved decisions"),
    ({"speech": "unknown"}, "speech must be resolved"),
    ({"replacement_target": "bottle"}, "requires a product asset"),
    ({"duration_seconds": float("nan")}, "finite positive"),
    ({"aspect_ratio": "unknown"}, "positive integer ratio"),
    ({"shots": [{"id": "S1", "start": 1, "end": 4, "prompt": "image_1"}]}, "without gaps"),
    ({"shots": [{"id": "S1", "start": 0, "end": 2, "prompt": "image_1"}]}, "do not cover"),
])
def test_final_rejects_unresolved_or_incomplete_packages(values, change, expected):
    values.update(change)
    assert any(expected in error for error in validate_values(values))


def test_video_mode_is_allowed_without_storyboard(values, tmp_path):
    video = tmp_path / "reference.mp4"
    video.write_bytes(b"reference asset existence only")
    values["reference_mode"] = "video"
    values["assets"] = [{"id": "video_1", "role": "video", "path": str(video)}]
    values["shots"][0]["prompt"] = "Use video_1; preserve the movement."
    assert validate_values(values) == []
    prompt = render_seedance_prompt(values)
    assert lint_prompt(prompt, "no", "video", "source order", 4) == []
    assert any("forbidden reference-video" in error for error in lint_prompt(prompt))


def test_assets_must_map_to_output_shots(values):
    values["replacement_target"] = "bottle"
    values["assets"].append({"id": "image_2", "role": "product", "path": values["assets"][0]["path"]})
    assert any("not mapped" in error for error in validate_values(values))
    values["shots"][0]["prompt"] = "Use image_1; replace the bottle using image_2."
    assert validate_values(values) == []
    values["shots"][0]["prompt"] = "Use image_2 only."
    assert any("primary reference asset ID" in error for error in validate_values(values))


def test_speech_mode_must_match_dialogue(values):
    values["dialogue_timeline"] = '00:00-00:02 Speaker says: "Hello."'
    assert "speech is marked absent, but dialogue is present" in lint_prompt(
        render_seedance_prompt(values), "no", "storyboard", "right to left", 4)


def test_dialogue_bounds_and_unresolved_text(values):
    values["speech"] = "yes"
    values["dialogue_timeline"] = '00:00-00:05 Speaker says: "Hello."'
    assert any("exceed output duration" in error for error in lint_prompt(
        render_seedance_prompt(values), "yes", "storyboard", "right to left", 4))
    values["dialogue_timeline"] = '00:00-00:02 Speaker says: "[unclear]"'
    assert "unresolved content found" in lint_prompt(
        render_seedance_prompt(values), "yes", "storyboard", "right to left", 4)


def test_plan_never_writes_final_and_final_validates_before_write(values, tmp_path):
    config = tmp_path / "values.json"
    values["confirmed"] = False
    config.write_text(json.dumps(values), encoding="utf-8")
    output = tmp_path / "package"
    command = [sys.executable, str(ROOT / "scripts/build_prompt_pack.py"),
               "--input", str(config), "--out-dir", str(output)]
    subprocess.run(command, check=True)
    plan = (output / "replacement_plan.md").read_text(encoding="utf-8")
    assert values["assets"][0]["path"] in plan
    assert not (output / "seedance_prompt.md").exists()
    result = subprocess.run(command + ["--stage", "final"], capture_output=True, text=True)
    assert result.returncode != 0
    assert not (output / "seedance_prompt.md").exists()
    values["confirmed"] = True
    config.write_text(json.dumps(values), encoding="utf-8")
    subprocess.run(command + ["--stage", "final"], check=True)
    approved_prompt = (output / "seedance_prompt.md").read_bytes()
    broken = copy.deepcopy(values)
    broken["shots"][0]["end"] = 9
    config.write_text(json.dumps(broken), encoding="utf-8")
    result = subprocess.run(command + ["--stage", "final"], capture_output=True)
    assert result.returncode != 0
    assert (output / "seedance_prompt.md").read_bytes() == approved_prompt


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="FFmpeg required")
def test_real_cut_video_extracts_auditable_frames(tmp_path):
    video = tmp_path / "cuts.mp4"
    subprocess.run([
        "ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=black:s=64x64:r=25:d=1",
        "-f", "lavfi", "-i", "color=white:s=64x64:r=25:d=0.12",
        "-f", "lavfi", "-i", "color=black:s=64x64:r=25:d=1",
        "-filter_complex", "[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]", "-map", "[v]", str(video),
    ], check=True)
    times, duration = probe_timestamps(str(video))
    cuts = detect_cuts(str(video), 0.3)
    assert len(cuts) == 2
    assert timing_info(video)["variable_frame_rate"] is False
    output = tmp_path / "output"
    subprocess.run([sys.executable, str(ROOT / "scripts/extract_storyboard.py"), "--video", str(video),
                    "--out-dir", str(output), "--max-frames", "6"], check=True)
    manifest = json.loads((output / "storyboard_timeline.json").read_text(encoding="utf-8"))
    assert len(manifest["shots"]) == 3
    assert {frame["shot_id"] for frame in manifest["frames"]} == {1, 2, 3}
    for frame in manifest["frames"]:
        assert times[frame["source_frame_index"]] == frame["timestamp"]
        with Image.open(output / "frames" / frame["frame"]) as image:
            intensity = image.convert("L").getpixel((image.width // 2, image.height // 2))
        assert intensity > 240 if frame["shot_id"] == 2 else intensity < 15
    assert abs(manifest["duration"] - duration) < 0.001


def test_vfr_rejected_before_heavy_model_import(monkeypatch, tmp_path):
    monkeypatch.setattr("scripts.make_depth_map_video.probe_timestamps",
                        lambda path: ([0, 0.04, 0.12, 0.16], 0.2))
    assert timing_info(tmp_path / "vfr.mp4")["variable_frame_rate"] is True
    monkeypatch.setattr(sys, "argv", ["depth", "--video", str(tmp_path / "vfr.mp4"), "--out-dir", str(tmp_path)])
    from scripts.make_depth_map_video import main

    with pytest.raises(SystemExit, match="Variable-frame-rate"):
        main()
