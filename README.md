# Video Dashi Skills

[English](README.md) | [简体中文](README.zh-CN.md)

A Codex skill and Python toolkit that converts local videos, Douyin share links, or storyboard images into structured, confirmation-gated Seedance reference packages. It supports storyboard extraction, dialogue transcription and cleanup, product-replacement planning, prompt generation, video enhancement, final-video super-resolution, and review-friendly motion-reference conversions.

This project prepares references and prompts. It does not call Seedance or generate the final creative video by itself.

## Features

- Resolve a local video or a Douyin share link into a local reference file.
- Inspect duration, resolution, frame rate, aspect ratio, and audio streams.
- Extract up to 24 representative frames and build `storyboard_grid.jpg`.
- Preserve raw ASR, clean transcripts, generate SRT subtitles, and build timestamped dialogue timelines.
- Analyze replacement products and create a shot-by-shot replacement plan.
- Generate and lint a Seedance prompt only after the user confirms the storyboard, replacement target, dialogue handling, duration, ratio, and audio mode.
- Enhance weak source footage with Real-ESRGAN or an FFmpeg fallback for clearer storyboard extraction.
- Upscale a completed AI-generated video with `realesr-animevideov3`.
- Create review-friendly flat animation, isolated person masks, or articulated 2.5D mannequin motion references.

## Workflow

1. Resolve the reference source.
2. Analyze the video and extract a storyboard.
3. Optionally enhance the source before extracting clearer frames.
4. Transcribe and clean speech without inventing missing words.
5. Ask the user to confirm the storyboard, dialogue, replacement target, duration, aspect ratio, and audio mode.
6. Analyze the product and prepare `replacement_plan.md`.
7. After confirmation, create and lint `seedance_prompt.md`.
8. Upload `storyboard_grid.jpg` to Seedance and paste the generated prompt.

The original or enhanced video is used for analysis and timing only. The final Seedance visual reference is the storyboard image unless the user explicitly requests video-to-video.

## Requirements

| Component | Required for | Notes |
| --- | --- | --- |
| Python 3.10+ | All scripts | Python 3.11 or 3.12 recommended. |
| FFmpeg and FFprobe | Video analysis, frames, encoding | Both commands must be available on `PATH`. |
| `requests` | Douyin download | Installed by `requirements.txt`. |
| `social-media-parser` skill | Douyin share links | Not needed for local files. |
| faster-whisper | Local ASR | Optional; installed by `requirements-ai.txt`. |
| Real-ESRGAN NCNN Vulkan | AI enhancement/upscale | Optional for source enhancement; required for final-video upscale. |
| OpenCV, NumPy | Review-friendly conversions | Installed by `requirements-ai.txt`. |
| PyTorch + Ultralytics | Person mask and mannequin modes | Install PyTorch for the target CUDA version separately. |
| Meta SAM 2 | Hybrid person-mask propagation | Optional; per-frame fallback is available. |

## Installation

### 1. Clone as a Codex skill

```powershell
pwsh -NoProfile -Command "git clone https://github.com/asen5269/video-dashi-skills.git `$HOME/.codex/skills/video-dashi-skills"
```

Restart Codex after installation so it can discover `SKILL.md`.

### 2. Install Python dependencies

Core resolver support:

```powershell
pwsh -NoProfile -Command "python -m pip install -r `$HOME/.codex/skills/video-dashi-skills/requirements.txt"
```

Optional ASR and computer-vision support:

```powershell
pwsh -NoProfile -Command "python -m pip install -r `$HOME/.codex/skills/video-dashi-skills/requirements-ai.txt"
```

Install PyTorch separately from the official PyTorch package source matching your CPU/CUDA environment. Install Meta SAM 2 separately if hybrid video-object propagation is required.

### 3. Install FFmpeg

Verify:

```powershell
pwsh -NoProfile -Command "ffmpeg -version; ffprobe -version"
```

### 4. Optional Real-ESRGAN

Install `realesrgan-ncnn-vulkan` on `PATH`, or extract it anywhere below:

```text
video-dashi-skills/vendor/
```

The scripts search both `PATH` and `vendor/` recursively. Third-party binaries and model weights are intentionally excluded from this repository and remain under their upstream licenses.

### 5. Optional Douyin parser

Install `social-media-parser` at one of these locations:

```text
~/.codex/skills/social-media-parser/
~/.codex/skills/social-media-parser/social-media-parser/
```

You may also pass a custom directory with `--parser-root`.

## Quick Start

Set the skill and work directories:

```powershell
pwsh -NoProfile -Command "`$skill=`$HOME+'/.codex/skills/video-dashi-skills'; `$work='work/seedance-run'; python `$skill/scripts/resolve_reference_video.py --input 'C:/videos/reference.mp4' --out-dir `$work/source"
```

Read `work/seedance-run/source/reference_input.json`, then analyze the resolved video:

```powershell
pwsh -NoProfile -Command "python `$HOME/.codex/skills/video-dashi-skills/scripts/analyze_video.py --video 'C:/videos/reference.mp4' --out 'work/seedance-run/video_analysis.json'"
```

Create a storyboard:

```powershell
pwsh -NoProfile -Command "python `$HOME/.codex/skills/video-dashi-skills/scripts/extract_storyboard.py --video 'C:/videos/reference.mp4' --out-dir 'work/seedance-run' --max-frames 24"
```

Generated files include `frames/` and `storyboard_grid.jpg`.

## Core Commands

### Inspect source quality

```powershell
pwsh -NoProfile -Command "python `$HOME/.codex/skills/video-dashi-skills/scripts/check_video_quality.py --video 'C:/videos/reference.mp4' --out 'work/seedance-run/video_quality.json'"
```

### Enhance the source for storyboard extraction

```powershell
pwsh -NoProfile -Command "python `$HOME/.codex/skills/video-dashi-skills/scripts/enhance_video.py --video 'C:/videos/reference.mp4' --out-dir 'work/seedance-run/enhanced' --backend auto --profile compressed --scale 2"
```

`auto` uses Real-ESRGAN when available and otherwise falls back to FFmpeg. The enhanced file is for clearer analysis frames, not the final Seedance reference.

### Transcribe and clean dialogue

```powershell
pwsh -NoProfile -Command "python `$HOME/.codex/skills/video-dashi-skills/scripts/transcribe_audio.py --video 'C:/videos/reference.mp4' --out 'work/seedance-run/raw_transcript.txt' --srt-out 'work/seedance-run/raw_subtitles.srt'"
```

```powershell
pwsh -NoProfile -Command "python `$HOME/.codex/skills/video-dashi-skills/scripts/clean_transcript.py --input 'work/seedance-run/raw_transcript.txt' --clean-out 'work/seedance-run/clean_transcript.md' --timeline-out 'work/seedance-run/dialogue_timeline.md' --srt-out 'work/seedance-run/subtitles.srt'"
```

The agent must review the cleaned transcript. Uncertain speech is marked `[unclear]` and must be confirmed before final prompt generation.

### Build and validate a prompt pack

After the required confirmation gate, create `prompt_values.json` and run:

```powershell
pwsh -NoProfile -Command "python `$HOME/.codex/skills/video-dashi-skills/scripts/build_prompt_pack.py --input 'work/seedance-run/prompt_values.json' --out-dir 'work/seedance-run'"
```

Validate a prompt independently:

```powershell
pwsh -NoProfile -Command "python `$HOME/.codex/skills/video-dashi-skills/scripts/lint_seedance_prompt.py --prompt 'work/seedance-run/seedance_prompt.md' --speech unknown"
```

### Upscale a completed video

```powershell
pwsh -NoProfile -Command "python `$HOME/.codex/skills/video-dashi-skills/scripts/upscale_video.py --video 'C:/videos/final.mp4' --out-dir 'work/seedance-run/upscaled' --scale 2 --target-height 1080 --model realesr-animevideov3 --tile 0"
```

Final-video super-resolution requires Real-ESRGAN. FFmpeg-only scaling is intentionally not used for this delivery phase.

### Review-friendly flat animation

```powershell
pwsh -NoProfile -Command "python `$HOME/.codex/skills/video-dashi-skills/scripts/make_jimeng_review_friendly.py --video 'C:/videos/reference.mp4' --out-dir 'work/jimeng-review'"
```

### Person mask

```powershell
pwsh -NoProfile -Command "python `$HOME/.codex/skills/video-dashi-skills/scripts/make_jimeng_person_mask.py --video 'C:/videos/reference.mp4' --out-dir 'work/jimeng-person-mask'"
```

CUDA is required by default. `--allow-cpu` is available but very slow. Hybrid mode uses SAM 2 and falls back to per-frame YOLO/SAM refinement when SAM 2 VOS is unavailable.

### Articulated 2.5D mannequin

```powershell
pwsh -NoProfile -Command "python `$HOME/.codex/skills/video-dashi-skills/scripts/make_jimeng_joint_mannequin.py --video 'C:/videos/reference.mp4' --out-dir 'work/jimeng-joint-mannequin'"
```

This is a tracked 2.5D pose representation, not a recovered 3D human mesh.

## Output Contract

Depending on the selected workflow, the skill creates:

```text
source/reference_input.json
source/reference_video.mp4
video_analysis.json
video_quality.json
frames/
storyboard_grid.jpg
enhanced/enhanced_reference.mp4
enhanced/enhancement_metadata.json
raw_transcript.txt
clean_transcript.md
dialogue_timeline.md
subtitles.srt
shot_analysis.md
product_analysis.md
replacement_plan.md
seedance_prompt.md
upscaled/upscaled_video.mp4
upscaled/upscale_metadata.json
```

## Safety and Content Rules

- Replace only the object explicitly confirmed by the user.
- Preserve people, hands, pose, background, lighting, camera, edit timing, and CTA unless changes are explicitly requested.
- Never invent dialogue, product claims, names, amounts, or timestamps.
- Remove audio only by default in review-reference modes; keep it only when authorized.
- Remove overlays or watermarks only after identifying a verified rectangle and confirming the content may be modified.
- “Review-friendly” does not guarantee platform approval and must not be used to conceal independently prohibited content.

## Project Structure

```text
SKILL.md                 Codex behavior and workflow contract
scripts/                 Executable Python tools
templates/               Replacement-plan and prompt templates
fixtures/                Test metadata
tests/                   Pytest suite
requirements.txt         Core Python dependency
requirements-ai.txt      Optional ASR/CV dependencies
```

## Tests

```powershell
pwsh -NoProfile -Command "python -m pytest tests -q"
```

Some tests or modes require FFmpeg, GPU packages, model weights, or third-party executables.

## Troubleshooting

- `ffmpeg` or `ffprobe` not found: install FFmpeg and add its `bin` directory to `PATH`.
- `social-media-parser skill not found`: install the parser in the expected Codex skill path or use `--parser-root`.
- `realesrgan-ncnn-vulkan not found`: add the executable to `PATH` or place the extracted package below `vendor/`.
- CUDA error: install a PyTorch build matching the installed NVIDIA driver/CUDA runtime, or use `--allow-cpu` where supported.
- SAM 2 unavailable: person-mask hybrid mode reports the fallback and uses per-frame refinement.
- Merged or missing limbs: heavy occlusion and motion blur require manual keyframe correction or professional rotoscoping.

## License

Original source code and documentation are licensed under the [MIT License](LICENSE). FFmpeg, Real-ESRGAN, model weights, PyTorch, Ultralytics, SAM 2, and other third-party components are governed by their own licenses.
