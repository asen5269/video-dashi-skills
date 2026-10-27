---
name: video-dashi-skills
description: Analyze a local video, storyboard image, or Douyin share link and prepare a Seedance reference package, including product replacement plans and reviewed dialogue timelines. Also supports video enhancement, final-video upscale, relative-depth video, person masks and articulated mannequin motion references. Use for 分镜分析、商品替换、Seedance 提示词、深度黑白视频、人物遮罩 or 白模绿幕.
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
- For monochrome depth-map video, read [references/depth-map-video.md](references/depth-map-video.md).
- For transcript cleanup, replacement planning, and final prompt generation, read [references/prompt-workflow.md](references/prompt-workflow.md).
- For review-friendly animation, person masks, or articulated mannequins, read [references/jimeng-reference-modes.md](references/jimeng-reference-modes.md).

Read only the reference needed for the active request.

Analysis-only, enhancement, upscale, depth and mask requests finish with their own deliverables; do not force product questions or a prompt confirmation gate onto them. Use the core workflow below only for a Seedance prompt package.

## Hard Rules

- Accept a local video, storyboard image, or Douyin share text/link.
- Use the bundled `scripts/douyin_parser.py`; never depend on another local Skill.
- Do not assume 9:16, silence, duration, or frame order when the source proves otherwise.
- Default to storyboard-image reference. For explicitly requested video-to-video, list the source video as the uploaded motion/timing reference and use video-mode validation.
- Use `storyboard_grid.jpg` as the primary Seedance visual reference unless the user explicitly requests video-to-video.
- Prepare the complete review plan before requesting confirmation. Generate the final prompt only after its reference assets, order, replacement target (or none), dialogue handling, duration, aspect ratio, and audio mode are confirmed. Reuse explicit choices already supplied; ask again only for changed or unresolved decisions.
- Preserve raw ASR before editing it. Never invent dialogue, names, amounts, claims, or timestamps.
- Replace only the user-confirmed object. Preserve people, hands, pose, scene, lighting, camera, shot order, timing, subtitles, and CTA unless explicitly changed.
- Use enhanced video only to extract clearer frames. Never present it as the final Seedance reference.
- Use `upscale_video.py`, not `enhance_video.py`, for a completed final video.
- Use `make_depth_map_video.py` for 深度黑白视频. Default mapping is near=white and far=black. Its fixed-fps encoder does not preserve variable-frame-rate timestamps; follow the depth reference's timing limitations and verification.
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

Infer video duration and ratio from the source and include them in the review plan. Do not infer output ratio from the dimensions of a multi-panel storyboard. Never default audio to silent outside modes that explicitly document that default; state audio removal in the proposed transformation and honor the user's existing authorization.

### 2. Resolve the Source

```powershell
pwsh -NoProfile -Command "python '<SKILL_ROOT>/scripts/resolve_reference_video.py' --input '<VIDEO_PATH_OR_DOUYIN_SHARE_TEXT>' --out-dir '<OUTPUT_DIR>/source'"
```

Read `<OUTPUT_DIR>/source/reference_input.json`:

- `local_video` or `social_link`: use `video_path` and continue below.
- `storyboard_image`: use `image_path` as the visual reference; do not run FFprobe, video extraction or ASR on it. Inspect panel numbering, people, objects and any readable text. Record unknown duration, speech, audio, output ratio and motion in the review plan. Readable subtitles are not verified spoken dialogue. Request only missing decisions needed for the final package. Preserve supplied panel order; ask if ambiguous.

If a Douyin post contains images but no video, report this and request a local storyboard image if the user wants the image branch.

### 3. Analyze and Extract Storyboard

```powershell
pwsh -NoProfile -Command "python '<SKILL_ROOT>/scripts/analyze_video.py' --video '<RESOLVED_VIDEO_PATH>' --out '<OUTPUT_DIR>/video_analysis.json'"
```

```powershell
pwsh -NoProfile -Command "python '<SKILL_ROOT>/scripts/extract_storyboard.py' --video '<RESOLVED_VIDEO_PATH>' --out-dir '<OUTPUT_DIR>' --max-frames 24"
```

Report duration, resolution, fps, aspect ratio, audio presence, extracted frame count, and storyboard path. Read `storyboard_timeline.json`: it records detected shot intervals and each sampled frame's source index and timestamp relative to the first video frame. Grid labels distinguish frames (`F`) from detected shots (`S`).

Visually review automatic cut candidates: flashes, transitions and very similar shots may produce false or missed cuts. Increase the frame cap when shot count exceeds it; never silently omit detected shots. Add manually selected action/interaction keyframes if the automatic samples miss important motion or occlusion; update the manifest and grid together. Read generated grids left to right and top to bottom; preserve explicit order on supplied storyboards.

Static grids provide appearance, pose and order references, not exact camera motion, timing or continuity. Write those targets in the shot timeline, describe reconstruction as approximate, and use video reference when explicitly requested for motion. Do not promise exact product, logo, hand or subtitle preservation from a prompt alone.

### 4. Handle Audio and Dialogue

If speech exists, read [references/prompt-workflow.md](references/prompt-workflow.md), preserve raw ASR and create a cleaned transcript. ASR segment boundaries are provisional; listen against the source before calling them reviewed. For word-level or lip-sync precision, use an available forced-aligner or manual timing review; the bundled ASR is not forced alignment. Put uncertain lines and timing in the review plan together.

If audio is music-only, preserve its timing unless the user requests removal.

### 5. Prepare and Confirm Once

Read [references/prompt-workflow.md](references/prompt-workflow.md). Inspect product references when replacement is requested, create `product_analysis.md` and a complete `replacement_plan.md` with `--stage plan`. Include:

- the actual primary reference (generated grid, supplied storyboard, or explicitly requested video)
- frame reading order
- cleaned dialogue and dialogue handling
- replacement target and replacement product
- preserved people, hands, pose, scene, subtitles, and CTA
- duration, aspect ratio, and audio mode
- shot intervals covering the output duration, the source-to-output mapping, and any reconstructed motion
- upload asset IDs and absolute paths, including replacement product images
- all unresolved dialogue, timing or identity questions

Show the plan and ask one consolidated confirmation question for missing or changed decisions. Treat `none` as a valid replacement target. No product image is required when nothing is replaced. If the user already explicitly approved the complete unchanged plan, proceed without repeating the question. Record `confirmed=true` only after confirmation; it is a workflow record, not proof of user authorization.

### 6. Plan and Generate

After confirmation, generate with `--stage final`. Resolve `speech` to `yes` or `no`; never use `unknown` to skip required dialogue checks. The generator validates assets and full shot coverage before writing the prompt. Changes to the agreed assets, target, order, dialogue or output settings invalidate confirmation until the affected changes are approved.

Tell the user:

```text
Upload the listed primary reference and every product reference using the asset IDs in seedance_prompt.md, then paste the prompt. For video mode, upload the listed video instead of the storyboard as the primary reference.
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
storyboard_timeline.json
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
prompt_values.json
upscaled/upscaled_video.mp4
upscaled/upscale_metadata.json
depth-map/depth_bw.mp4
depth-map/depth_map_metadata.json
```

Always report the absolute paths of generated deliverables.

## Verification

Validate the final prompt:

```powershell
pwsh -NoProfile -Command "python '<SKILL_ROOT>/scripts/lint_seedance_prompt.py' --prompt '<OUTPUT_DIR>/seedance_prompt.md' --speech '<yes_OR_no>' --reference-mode '<storyboard_OR_video>' --frame-order '<CONFIRMED_ORDER>' --duration-seconds <OUTPUT_SECONDS>"
```

Verify video deliverables with FFprobe. Check resolution, duration, frame rate, audio presence, file size, and expected frame count before reporting completion.
Compare source/output timing explicitly; a matching nominal fps is not proof of matching frame timestamps. State actual discrepancies and model limitations. Verify the asset manifest matches the files delivered; list all uploads and their absolute paths.
