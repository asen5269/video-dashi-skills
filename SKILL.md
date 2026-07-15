---
name: video-dashi-skills
description: Turn a local video, storyboard image, or Douyin share link into a confirmed Seedance reference package. Use for video analysis, storyboard extraction, exact dialogue timelines, product replacement planning, Seedance prompts, source enhancement, final-video super-resolution, person masks, review-friendly animation, or articulated 2.5D mannequin references. Trigger on requests such as 商品替换, 分镜分析, Seedance 提示词, 视频超分, 人物遮罩, 白模绿幕, 即梦审核友好版, or 把视频处理为即梦可过审.
---

# Video Dashi Skills

Build reproducible reference artifacts from user-provided media. Keep analysis, confirmation, prompt generation, and delivery as separate phases.

## Resolve Paths

Set `<SKILL_ROOT>` to the absolute directory containing this `SKILL.md`. Run bundled scripts with absolute paths:

```powershell
pwsh -NoProfile -Command "python '<SKILL_ROOT>/scripts/<SCRIPT>.py' <ARGS>"
```

Never assume the current working directory contains `skills/`.

## Route the Request

- For source enhancement or final-video upscale, read [references/video-enhancement.md](references/video-enhancement.md).
- For transcript cleanup, replacement planning, and final prompt generation, read [references/prompt-workflow.md](references/prompt-workflow.md).
- For review-friendly animation, person masks, or articulated mannequins, read [references/jimeng-reference-modes.md](references/jimeng-reference-modes.md).

Read only the reference needed for the active request.

## Hard Rules

- Accept a local video, storyboard image, or Douyin share text/link.
- Use the bundled `scripts/douyin_parser.py`; never depend on another local Skill.
- Do not assume 9:16, silence, duration, or frame order when the source proves otherwise.
- Use the original video only for frames, timing, motion, composition, audio, and shot analysis.
- Use `storyboard_grid.jpg` as the primary Seedance visual reference unless the user explicitly requests video-to-video.
- Do not generate the final prompt before the user confirms the storyboard, replacement target, dialogue handling, duration, aspect ratio, and audio mode.
- Preserve raw ASR before editing it. Never invent dialogue, names, amounts, claims, or timestamps.
- Replace only the user-confirmed object. Preserve people, hands, pose, scene, lighting, camera, shot order, timing, subtitles, and CTA unless explicitly changed.
- Use enhanced video only to extract clearer frames. Never present it as the final Seedance reference.
- Use `upscale_video.py`, not `enhance_video.py`, for a completed final video.
- Never promise platform approval. Describe review conversions as review-friendly or compliance-oriented.
- Do not remove overlays, watermarks, or audio without confirming the user may modify them.
- Stop if the underlying content is illegal or disallowed independent of its style, face, audio, or watermark.

## Core Workflow

### 1. Intake

Identify:

- source path, storyboard path, or Douyin share text
- product image paths and exact replacement target
- brand text or CTA changes
- duration and aspect ratio preference
- preserve, rewrite, translate, or remove dialogue
- keep or remove audio
- whether source enhancement is needed

Infer missing duration and ratio from the source, then ask for confirmation. Never default audio to silent outside review-reference modes.

### 2. Resolve the Source

```powershell
pwsh -NoProfile -Command "python '<SKILL_ROOT>/scripts/resolve_reference_video.py' --input '<VIDEO_PATH_OR_DOUYIN_SHARE_TEXT>' --out-dir '<OUTPUT_DIR>/source'"
```

Read `<OUTPUT_DIR>/source/reference_input.json` and use its `video_path`. If a Douyin post contains images but no video, stop and report that it is not a downloadable video reference.

### 3. Analyze and Extract Storyboard

```powershell
pwsh -NoProfile -Command "python '<SKILL_ROOT>/scripts/analyze_video.py' --video '<RESOLVED_VIDEO_PATH>' --out '<OUTPUT_DIR>/video_analysis.json'"
```

```powershell
pwsh -NoProfile -Command "python '<SKILL_ROOT>/scripts/extract_storyboard.py' --video '<RESOLVED_VIDEO_PATH>' --out-dir '<OUTPUT_DIR>' --max-frames 24"
```

Report duration, resolution, fps, aspect ratio, audio presence, extracted frame count, and storyboard path. Read frames left to right and top to bottom unless explicit numbering says otherwise.

### 4. Handle Audio and Dialogue

If speech exists, read [references/prompt-workflow.md](references/prompt-workflow.md), preserve raw ASR, create a cleaned transcript, and flag uncertain lines as `[unclear]`. Ask the user to confirm every uncertain line.

If audio is music-only, preserve its timing unless the user requests removal.

### 5. Confirmation Gate

Before product planning or final prompt generation, ask the user to confirm:

- `storyboard_grid.jpg` is the visual reference
- frame reading order
- cleaned dialogue and dialogue handling
- replacement target and replacement product
- preserved people, hands, pose, scene, subtitles, and CTA
- duration, aspect ratio, and audio mode

Do not bypass this gate.

### 6. Plan and Generate

Read [references/prompt-workflow.md](references/prompt-workflow.md). Create `product_analysis.md`, prepare `replacement_plan.md`, obtain confirmation, then build and lint `seedance_prompt.md`.

Tell the user:

```text
Upload storyboard_grid.jpg to Seedance, then paste seedance_prompt.md.
```

## Output Contract

Create when applicable:

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
raw_subtitles.srt
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

Always report the absolute paths of generated deliverables.

## Verification

Validate the final prompt:

```powershell
pwsh -NoProfile -Command "python '<SKILL_ROOT>/scripts/lint_seedance_prompt.py' --prompt '<OUTPUT_DIR>/seedance_prompt.md' --speech unknown"
```

Verify video deliverables with FFprobe. Check resolution, duration, frame rate, audio presence, file size, and expected frame count before reporting completion.
