# Video Dashi Skills

[![CI](https://github.com/asen5269/video-dashi-skills/actions/workflows/ci.yml/badge.svg)](https://github.com/asen5269/video-dashi-skills/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[English](README.md) | [简体中文](README.zh-CN.md)

A production-oriented Codex Skill for turning a local video, a Douyin share link, or an existing storyboard into a confirmed Seedance reference package.

It combines deterministic Python tools with an agent workflow for video inspection, storyboard extraction, exact dialogue handling, product replacement planning, prompt generation, source enhancement, final-video super-resolution, and review-friendly motion references.

## What This Project Is

- A directly installable Codex Skill with valid `SKILL.md` metadata.
- A self-contained toolkit: Douyin parsing is bundled and does not call another local Skill.
- A confirmation-gated workflow: final prompts are generated only after the user confirms the visual reference and edit intent.
- A reproducible artifact pipeline: each phase writes inspectable files rather than hiding state in an agent conversation.

## What This Project Is Not

- It does not call Seedance or generate the final creative video.
- It does not guarantee review approval on Seedance, Jimeng, or any other platform.
- It does not bypass login, paywalls, DRM, private content, or platform moderation.
- It does not treat the source video as the primary Seedance reference unless the user explicitly asks for video-to-video.

## Capabilities

| Capability | Input | Main output |
| --- | --- | --- |
| Source resolution | Local video or Douyin share text/link | `source/reference_input.json`, local reference video |
| Video analysis | Local video | `video_analysis.json` |
| Storyboard extraction | Local or enhanced video | `frames/`, `storyboard_grid.jpg` |
| Speech transcription | Video with speech | raw transcript and raw SRT |
| Transcript cleanup | Raw ASR | cleaned transcript, timeline, subtitles |
| Product replacement planning | Storyboard and product images | `product_analysis.md`, `replacement_plan.md` |
| Seedance prompt generation | Confirmed plan | `seedance_prompt.md` plus lint result |
| Source enhancement | Low-quality reference video | enhanced video for clearer storyboard frames |
| Final-video upscale | Completed generated video | upscaled delivery video and metadata |
| Flat review reference | Video | non-photorealistic motion reference |
| Person mask | Video | tracked person-mask video |
| 2.5D mannequin | Video | articulated white-mannequin green-screen video |

## Design

```text
User media
   │
   ├─ local path ──────────────────────┐
   └─ Douyin share text → built-in parser
                                      │
                              resolved video
                                      │
                     analysis + storyboard + ASR
                                      │
                             user confirmation
                                      │
                      replacement plan + prompt
                                      │
                         linted artifact package
```

The agent owns decisions and confirmation gates. Python scripts own repeatable media inspection, parsing, rendering, formatting, and validation.

## Repository Layout

```text
video-dashi-skills/
├── SKILL.md                         Agent workflow and trigger metadata
├── agents/openai.yaml              Codex UI metadata
├── references/                     Details loaded only for relevant modes
│   ├── prompt-workflow.md
│   ├── video-enhancement.md
│   └── jimeng-reference-modes.md
├── scripts/                         Deterministic Python tools
├── templates/                       Prompt and replacement-plan templates
├── fixtures/                        Test metadata
├── tests/                           Unit tests
├── requirements.txt                 Core resolver dependencies
├── requirements-ai.txt              Optional ASR/CV dependencies
├── requirements-dev.txt             Test and lint dependencies
├── pyproject.toml                    Pytest and Ruff configuration
└── .github/workflows/ci.yml          Linux and Windows validation
```

`SKILL.md` stays focused on the core workflow. Advanced modes live in `references/` so Codex loads only the instructions needed for the active request.

## Requirements

### Core

- Codex with local Skill discovery
- Python 3.10 or newer; 3.11 or 3.12 recommended
- FFmpeg and FFprobe available on `PATH`
- Public source media that the user is authorized to process

### Optional

| Component | Required for |
| --- | --- |
| faster-whisper | Local ASR |
| Real-ESRGAN NCNN Vulkan | AI source enhancement and final-video upscale |
| OpenCV and NumPy | Review-friendly rendering |
| PyTorch and Ultralytics | Person-mask and mannequin modes |
| Meta SAM 2 | Hybrid video-object mask propagation |
| NVIDIA CUDA | Practical GPU execution for mask/mannequin modes |

## Installation

### Install as a Codex Skill

PowerShell:

```powershell
pwsh -NoProfile -Command "git clone https://github.com/asen5269/video-dashi-skills.git `$HOME/.codex/skills/video-dashi-skills"
```

If the directory already exists:

```powershell
pwsh -NoProfile -Command "git -C `$HOME/.codex/skills/video-dashi-skills pull --ff-only"
```

Restart Codex after the first installation so it discovers `SKILL.md` and `agents/openai.yaml`.

### Install Core Dependencies

```powershell
pwsh -NoProfile -Command "python -m pip install -r `$HOME/.codex/skills/video-dashi-skills/requirements.txt"
```

This installs `requests`, `certifi`, and `yt-dlp`. Douyin parsing is part of this repository; no separate parser Skill is needed.

### Install Optional AI Dependencies

```powershell
pwsh -NoProfile -Command "python -m pip install -r `$HOME/.codex/skills/video-dashi-skills/requirements-ai.txt"
```

Install PyTorch separately using the package source matching the machine's CPU or CUDA environment. Install Meta SAM 2 separately only when hybrid person-mask propagation is required.

### Install FFmpeg

Verify both commands:

```powershell
pwsh -NoProfile -Command "ffmpeg -version; ffprobe -version"
```

### Optional Real-ESRGAN

Put `realesrgan-ncnn-vulkan` on `PATH`, or extract its package below:

```text
video-dashi-skills/vendor/
```

The scripts search `PATH` and `vendor/` recursively. Third-party executables, model weights, sample media, and archives are intentionally excluded from Git.

## Invoke the Skill

Example prompts:

```text
Use $video-dashi-skills to analyze this video and create a Seedance storyboard package.
```

```text
Use $video-dashi-skills to replace the bottle in this Douyin video with my uploaded product. Preserve the person, hand movement, scene, dialogue, and camera.
```

```text
Use $video-dashi-skills to upscale this completed AI video from 720p to 1080p.
```

```text
Use $video-dashi-skills to create a 2.5D white-mannequin green-screen action reference.
```

## Manual Quick Start

The Skill normally runs these commands through Codex. They can also be executed manually.

Set the absolute Skill path:

```powershell
pwsh -NoProfile -Command "`$skill=`$HOME+'/.codex/skills/video-dashi-skills'; python `$skill/scripts/resolve_reference_video.py --input 'C:/videos/reference.mp4' --out-dir 'work/seedance-run/source'"
```

Analyze the resolved video:

```powershell
pwsh -NoProfile -Command "python `$HOME/.codex/skills/video-dashi-skills/scripts/analyze_video.py --video 'C:/videos/reference.mp4' --out 'work/seedance-run/video_analysis.json'"
```

Extract a storyboard:

```powershell
pwsh -NoProfile -Command "python `$HOME/.codex/skills/video-dashi-skills/scripts/extract_storyboard.py --video 'C:/videos/reference.mp4' --out-dir 'work/seedance-run' --max-frames 24"
```

The agent then inspects the storyboard, handles dialogue, collects confirmation, and generates the replacement plan and prompt.

## Confirmation Gate

Before final prompt generation, the Skill requires confirmation of:

- `storyboard_grid.jpg` as the visual reference
- storyboard reading order
- exact cleaned dialogue and its handling
- replacement target and replacement product
- preserved people, hands, pose, scene, subtitles, and CTA
- output duration and aspect ratio
- audio mode

This gate prevents a technically valid prompt from silently encoding the wrong creative decision.

## Output Package

Depending on the selected workflow:

```text
work/seedance-run/
├── source/
│   ├── reference_input.json
│   └── reference_video.mp4
├── video_analysis.json
├── video_quality.json
├── frames/
├── storyboard_grid.jpg
├── enhanced/
│   ├── enhanced_reference.mp4
│   └── enhancement_metadata.json
├── raw_transcript.txt
├── raw_subtitles.srt
├── clean_transcript.md
├── dialogue_timeline.md
├── subtitles.srt
├── shot_analysis.md
├── product_analysis.md
├── replacement_plan.md
├── prompt_values.json
└── seedance_prompt.md
```

Final-video upscale and Jimeng reference modes write separate subdirectories with their own metadata files.

## Advanced Modes

- [Transcript, replacement, and prompt workflow](references/prompt-workflow.md)
- [Video enhancement and final-video super-resolution](references/video-enhancement.md)
- [Jimeng review-friendly reference modes](references/jimeng-reference-modes.md)

## Development

Install development dependencies:

```powershell
pwsh -NoProfile -Command "python -m pip install -r requirements-dev.txt"
```

Validate the package:

```powershell
pwsh -NoProfile -Command "python scripts/validate_skill.py ."
```

Run lint and tests:

```powershell
pwsh -NoProfile -Command "python -m ruff check scripts tests; python -m pytest"
```

CI runs Skill validation, syntax compilation, Ruff, and unit tests on Windows and Linux.

## Troubleshooting

- `ffmpeg` or `ffprobe` not found: add the FFmpeg `bin` directory to `PATH`.
- Douyin parsing returns no video: confirm the link is public and points to a video rather than an image post, then update `yt-dlp`.
- `realesrgan-ncnn-vulkan not found`: put the executable on `PATH` or below `vendor/`.
- CUDA error: install a PyTorch build compatible with the installed driver, or use `--allow-cpu` where supported.
- SAM 2 unavailable: person-mask hybrid mode falls back to per-frame refinement.
- Merged masks or missing limbs: severe blur and occlusion require manual keyframes or professional rotoscoping.
- Prompt lint failure: read `seedance_prompt.lint.txt`, fix the missing confirmation or reference rule, and run the linter again.

## Content and Safety Rules

- Process only content the user is authorized to use and modify.
- Never invent dialogue, product claims, names, amounts, or timestamps.
- Remove watermarks or overlays only after confirming authorization and measuring the exact region.
- Keep audio in review-reference modes only after the user confirms authorization.
- Never describe a review-friendly conversion as guaranteed approval.

## License

Original source code and documentation are licensed under the [MIT License](LICENSE).

FFmpeg, Real-ESRGAN, PyTorch, Ultralytics, SAM 2, model weights, and other third-party components remain governed by their own licenses.
