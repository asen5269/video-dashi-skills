---
name: seedance-reference-product-replacer
description: Use when the user uploads a video, storyboard image, or Douyin share link and wants Seedance prompts, video super-resolution, product replacement, transcript cleanup, dialogue timelines, overlay removal, articulated 2.5D white-mannequin green-screen video, or a compliance-oriented action-reference conversion requested as "把视频处理为即梦可过审", "即梦审核友好版", or similar wording.
---

# Seedance Reference Product Replacer

Use this skill when the user wants:
- video-to-storyboard analysis
- Douyin share link to storyboard analysis
- manual video upload/path to storyboard analysis
- storyboard-image-to-video prompting
- product replacement based on uploaded product images
- Seedance prompts from uploaded storyboard images
- final video super-resolution such as 720p to 1080p/4K
- compliance-oriented conversion of a video into a non-photorealistic, silent Jimeng action reference
- preserved camera, motion, pacing, composition, lighting, and edit rhythm

## Hard Rules

- Do not assume 9:16.
- Do not assume silent.
- Do not generate final Seedance prompts before user confirms replacement target and output settings.
- Final Seedance prompts must use the uploaded `storyboard_grid.jpg` as the primary visual reference.
- Do not tell Seedance to use the original video as the main reference unless the user explicitly asks for video-to-video.
- Use the original video only to extract frames, infer timing, and build storyboard/shot analysis.
- Use enhanced video only to extract clearer frames/storyboards; do not use enhanced video as final Seedance video reference.
- If the user asks to upscale the final rendered video, use `upscale_video.py`, not `enhance_video.py`.
- Video enhancement must preserve source aspect ratio, shot order, timing, motion, scene identity, and style.
- Do not over-sharpen, stylize, de-age, beautify, change faces, change products, or invent visual details during enhancement.
- Accept either a local uploaded video path or a pasted Douyin share link/share text as the reference source.
- If a Douyin link/share text is provided, parse/download it first with the local `social-media-parser` skill, then treat the downloaded file as the reference video.
- Do not use the Douyin/original video as the final Seedance video reference.
- Animate storyboard frames left to right, top to bottom, unless the storyboard has explicit numbering.
- If the source video has speech, voiceover, or dialogue, do not ignore it.
- Preserve raw ASR output before editing it.
- Post-edit ASR text before using it in `dialogue_timeline.md` or `seedance_prompt.md`.
- Do not summarize dialogue; preserve exact spoken lines with timestamps.
- Fix obvious ASR typos only when context makes the correction clear.
- If ASR is uncertain, mark `[unclear]` and ask the user to confirm before final prompt generation.
- Do not invent missing dialogue, names, amounts, product claims, or timestamps.
- Replace only the user-confirmed product or object.
- Preserve people, hands, pose, background, lighting, camera movement, shot order, transition timing, and CTA layout unless user explicitly changes them.
- Never promise or claim guaranteed review approval. Describe the result as compliance-oriented or review-friendly.
- Do not use this workflow to conceal prohibited content. Stop if the underlying content is illegal or disallowed independent of faces, audio, watermarks, or style.

## Workflow

### Phase 1: Intake

Ask for or identify:
- reference source: local uploaded video path, storyboard image path, or Douyin share link/share text
- storyboard image path if already available
- product image path(s)
- target replacement object
- optional brand text
- optional CTA text
- output duration preference
- output aspect ratio preference
- audio preference
- whether to enhance the reference video before storyboard extraction
- whether to preserve, rewrite, translate, or remove original speech/dialogue

If output settings are missing, infer from the reference video and ask for confirmation.

### Phase 2: Reference Source Resolution

If the user provides a local uploaded video path, resolve it directly.

If the user provides Douyin share text or a Douyin URL, run:

```powershell
pwsh -NoProfile -Command "python skills/seedance-reference-product-replacer/scripts/resolve_reference_video.py --input '<VIDEO_PATH_OR_DOUYIN_SHARE_TEXT>' --out-dir '<OUTPUT_DIR>/source'"
```

This writes:
- `<OUTPUT_DIR>/source/reference_input.json`
- `<OUTPUT_DIR>/source/reference_video.mp4` or another video extension when downloaded from Douyin

Use the `video_path` from `reference_input.json` as `<RESOLVED_VIDEO_PATH>` for the next steps.

If the parser returns an image/note post or no video URL, stop and report that the link is not a downloadable video reference.

### Phase 3: Video Analysis

Run:

```powershell
pwsh -NoProfile -Command "python skills/seedance-reference-product-replacer/scripts/analyze_video.py --video '<RESOLVED_VIDEO_PATH>' --out '<OUTPUT_DIR>/video_analysis.json'"
```

Then run:

```powershell
pwsh -NoProfile -Command "python skills/seedance-reference-product-replacer/scripts/extract_storyboard.py --video '<RESOLVED_VIDEO_PATH>' --out-dir '<OUTPUT_DIR>'"
```

For long Douyin videos, the storyboard extractor automatically caps the grid at 24 frames by default. Override only when needed:

```powershell
pwsh -NoProfile -Command "python skills/seedance-reference-product-replacer/scripts/extract_storyboard.py --video '<RESOLVED_VIDEO_PATH>' --out-dir '<OUTPUT_DIR>' --max-frames 24"
```

Report:
- duration
- resolution
- fps
- aspect ratio
- audio presence
- speech/dialogue presence if detected
- storyboard grid path
- extracted frame count

### Phase 3.5: Optional Video Super-Resolution

Use this only when the source is low-resolution, compressed, blurry, text-heavy, product-detail-heavy, or the user asks for clearer storyboard frames.

First inspect quality:

```powershell
pwsh -NoProfile -Command "python skills/seedance-reference-product-replacer/scripts/check_video_quality.py --video '<RESOLVED_VIDEO_PATH>' --out '<OUTPUT_DIR>/video_quality.json'"
```

Default enhancement strategy:
- realistic people/product footage: `--profile realistic --scale 2`
- product closeups: `--profile product --scale 2`
- compressed Douyin/video-platform footage: `--profile compressed --scale 2`
- game footage: `--profile game --scale 2`
- anime/cartoon footage: `--profile anime --scale 2`
- already clean 1080p+ footage: skip enhancement or use `--scale 1 --profile clean`

Run enhancement:

```powershell
pwsh -NoProfile -Command "python skills/seedance-reference-product-replacer/scripts/enhance_video.py --video '<RESOLVED_VIDEO_PATH>' --out-dir '<OUTPUT_DIR>/enhanced' --backend auto --profile realistic --scale 2"
```

Backend behavior:
- `auto` uses bundled or PATH `realesrgan-ncnn-vulkan`.
- If no AI backend is available, it falls back to ffmpeg high-quality 2x upscale, mild denoise, and mild sharpening.
- The output is `<OUTPUT_DIR>/enhanced/enhanced_reference.mp4`.
- The metadata is `<OUTPUT_DIR>/enhanced/enhancement_metadata.json`.

After enhancement, extract storyboard from the enhanced video:

```powershell
pwsh -NoProfile -Command "python skills/seedance-reference-product-replacer/scripts/extract_storyboard.py --video '<OUTPUT_DIR>/enhanced/enhanced_reference.mp4' --out-dir '<OUTPUT_DIR>' --max-frames 24"
```

Never tell Seedance to use `enhanced_reference.mp4` as a video reference. The final Seedance input remains `storyboard_grid.jpg` plus `seedance_prompt.md`.

### Phase 3.6: Final Video Super-Resolution

Use this when the user already has a generated final video and wants higher resolution output.

Do not run `realesrgan-x4plus` or `realesrgan-x4plus-anime` by default for AI-generated videos; they can create block/grid artifacts.
Run the full video with `realesr-animevideov3` unless the user explicitly asks for another model.

For 720p to 1080p:

```powershell
pwsh -NoProfile -Command "python skills/seedance-reference-product-replacer/scripts/upscale_video.py --video '<FINAL_VIDEO_PATH>' --out-dir '<OUTPUT_DIR>/upscaled' --backend auto --profile compressed --scale 2 --target-height 1080 --model realesr-animevideov3 --tile 0"
```

For vertical 720x1280 to vertical 2K 1440x2560:

```powershell
pwsh -NoProfile -Command "python skills/seedance-reference-product-replacer/scripts/upscale_video.py --video '<FINAL_VIDEO_PATH>' --out-dir '<OUTPUT_DIR>/upscaled' --backend auto --profile compressed --scale 2 --model realesr-animevideov3 --tile 0"
```

Backend behavior:
- `auto` uses bundled or PATH `realesrgan-ncnn-vulkan`.
- Final delivery super-resolution must use Real-ESRGAN. Do not use ffmpeg-only upscale for this phase.
- Default final-video model is `realesr-animevideov3`; use it for AI-generated videos unless the user asks for another model.
- Do not use `realesrgan-x4plus` or `realesrgan-x4plus-anime` for AI-generated videos unless the user explicitly requests them.
- The output is `<OUTPUT_DIR>/upscaled/upscaled_video.mp4`.
- The metadata is `<OUTPUT_DIR>/upscaled/upscale_metadata.json`.

### Phase 3.7: Jimeng Review-Friendly Action Reference

Use this when the user says `把视频处理为即梦可过审`, `即梦审核友好版`, or asks to reduce review failures while preserving body movement.

Goal: produce a compliance-oriented motion reference, not evade moderation. Preserve aspect ratio, duration, fps, frame order, full bodies, limb boundaries, blocking, and choreography.

Before processing, inspect representative frames and identify:
- realistic human faces or identity details
- unlicensed or unknown audio
- third-party watermarks, logos, subtitles, or overlays
- recognizable copyrighted characters or branded visual elements

Default conversion:
- remove all audio unless the user confirms it is original or authorized
- remove a verified third-party watermark/overlay with a tightly measured normalized rectangle
- convert every frame to a flat four-tone non-photorealistic animation style
- soften facial texture while retaining head, body, hands, legs, pose, and motion silhouettes
- encode H.264 `yuv420p`, preserve source resolution/fps/duration, and target a practical upload size
- validate frame count, audio stream absence/presence, resolution, duration, and output size

Run:

```powershell
pwsh -NoProfile -Command "python skills/seedance-reference-product-replacer/scripts/make_jimeng_review_friendly.py --video '<VIDEO_PATH>' --out-dir '<OUTPUT_DIR>/jimeng-review'"
```

If a watermark is confirmed, pass a normalized `x,y,w,h` rectangle after inspecting frames:

```powershell
pwsh -NoProfile -Command "python skills/seedance-reference-product-replacer/scripts/make_jimeng_review_friendly.py --video '<VIDEO_PATH>' --out-dir '<OUTPUT_DIR>/jimeng-review' --watermark-rect '0.43,0.89,0.16,0.11'"
```

Use `--keep-audio` only after the user confirms the audio is original or authorized.

Outputs:
- `<OUTPUT_DIR>/jimeng-review/jimeng_review_friendly.mp4`
- `<OUTPUT_DIR>/jimeng-review/jimeng_review_metadata.json`

Report exactly what changed and state that platform approval is not guaranteed.

#### High-Fidelity Person Mask Mode

Use this mode when the user wants the original background preserved and asks for `人物自动遮罩`, `自动打码`, `描边人物`, or a screenshot-like full-body mask.

Pipeline:
- use hybrid mode by default: run YOLO11s-seg every 24 frames, then use SAM 2.1 Tiny VOS to propagate separate person masks within that short window
- reinitialize SAM2 from fresh YOLO detections at each window boundary to limit drift, recover from cuts, and detect people entering the scene
- use `--redetect-interval 12` for fast motion/cuts, `24` by default, or `48` for slower footage with limited GPU memory pressure
- fall back automatically to per-frame YOLO + SAM refinement only when the SAM2 VOS package is unavailable; force it with `--mode per-frame`
- in per-frame mode, intersect the SAM mask with the corresponding YOLO instance mask dilated by 15px and restrict it to the detection box expanded by 5%
- keep only the largest connected component
- apply median 9px smoothing and 5x5 opening/closing
- render each person independently with a vertical purple gradient
- draw a 1px antialiased white outline by default
- remove audio by default and remove only confirmed third-party watermarks

Default parameters:

```text
detector: yolo11s-seg.pt
SAM: sam2.1_t.pt
mode: hybrid
redetection interval: 24 frames
detector imgsz: 1280
SAM imgsz: 1024
confidence: 0.08
IoU: 0.50
coarse-mask dilation: 15px
box padding: 5%
median smoothing: 9px
morphology kernel: 5x5
outline: 1px
fill top: #2c0977
fill bottom: #180348
outline color: #ffffff
```

CUDA PyTorch is required by default. CPU processing is allowed only with `--allow-cpu` and is extremely slow.
Hybrid mode requires Meta's `sam2` package. If it is unavailable, the script reports the fallback and uses per-frame refinement.

Run:

```powershell
pwsh -NoProfile -Command "python skills/seedance-reference-product-replacer/scripts/make_jimeng_person_mask.py --video '<VIDEO_PATH>' --out-dir '<OUTPUT_DIR>/jimeng-person-mask'"
```

With a verified watermark rectangle:

```powershell
pwsh -NoProfile -Command "python skills/seedance-reference-product-replacer/scripts/make_jimeng_person_mask.py --video '<VIDEO_PATH>' --out-dir '<OUTPUT_DIR>/jimeng-person-mask' --watermark-rect '0.43,0.89,0.16,0.11'"
```

Outputs:
- `<OUTPUT_DIR>/jimeng-person-mask/jimeng_person_mask.mp4`
- `<OUTPUT_DIR>/jimeng-person-mask/jimeng_person_mask_metadata.json`

Limitations:
- heavy motion blur, full occlusion, and touching people can still merge or lose limbs
- automatic masks cannot reconstruct invisible body boundaries
- use keyframe manual correction or professional rotoscoping when reference-grade contours are required

#### 2.5D Articulated White-Mannequin Green-Screen Mode

Use this mode when the user asks for `白模绿幕`, `关节白模`, `骨骼白模`, `2.5D动作参考`, or wants people removed while preserving visible articulated motion.

Pipeline:
- use YOLO11 Pose to detect 17 COCO body joints for each person
- use BoT-SORT track IDs to keep people stable across frames
- smooth visible joints over time and briefly hold low-confidence joints to reduce flicker
- render head, torso, limb capsules, and visible joint spheres as a segmented white mannequin
- render only the mannequins over a solid chroma-green `#00ff00` background
- remove audio by default; preserve it only after the user confirms authorization

Run:

```powershell
pwsh -NoProfile -Command "python skills/seedance-reference-product-replacer/scripts/make_jimeng_joint_mannequin.py --video '<VIDEO_PATH>' --out-dir '<OUTPUT_DIR>/jimeng-joint-mannequin'"
```

For fast motion or jitter, lower smoothing latency with `--smooth-alpha 0.8`. For steadier motion, use `--smooth-alpha 0.5`.

Outputs:
- `<OUTPUT_DIR>/jimeng-joint-mannequin/jimeng_joint_mannequin.mp4`
- `<OUTPUT_DIR>/jimeng-joint-mannequin/jimeng_joint_mannequin_metadata.json`

Default parameters:

```text
pose model: yolo11n-pose.pt
tracker: botsort.yaml
pose resolution: 960
person confidence: 0.15
keypoint confidence: 0.25
smoothing alpha: 0.65
missing-joint hold: 6 frames
green: #00ff00
fill: #f4f4f4
joint: #d8d8d8
outline: #9a9a9a
```

Limitations:
- this is a 2.5D articulated representation, not a recovered 3D SMPL mesh
- fully hidden limbs cannot be reconstructed reliably
- severe overlap can swap tracker IDs; inspect multi-person outputs before delivery

### Phase 4: Dialogue and Storyboard Confirmation Gate

If audio exists:
- extract or inspect the audio
- run ASR/transcription when an ASR tool is available
- save unedited ASR as `raw_transcript.txt`
- post-edit the transcript into `clean_transcript.md`
- create `subtitles.srt`
- create `dialogue_timeline.md`
- distinguish speech/dialogue from music-only audio

Run ASR:

```powershell
pwsh -NoProfile -Command "python skills/seedance-reference-product-replacer/scripts/transcribe_audio.py --video '<RESOLVED_VIDEO_PATH>' --out '<OUTPUT_DIR>/raw_transcript.txt' --srt-out '<OUTPUT_DIR>/raw_subtitles.srt'"
```

Create an initial cleanup scaffold:

```powershell
pwsh -NoProfile -Command "python skills/seedance-reference-product-replacer/scripts/clean_transcript.py --input '<OUTPUT_DIR>/raw_transcript.txt' --clean-out '<OUTPUT_DIR>/clean_transcript.md' --timeline-out '<OUTPUT_DIR>/dialogue_timeline.md' --srt-out '<OUTPUT_DIR>/subtitles.srt'"
```

Then the agent must edit `clean_transcript.md` itself using the cleanup rules below. After editing, regenerate `dialogue_timeline.md` and `subtitles.srt` from the cleaned transcript:

```powershell
pwsh -NoProfile -Command "python skills/seedance-reference-product-replacer/scripts/clean_transcript.py --input '<OUTPUT_DIR>/clean_transcript.md' --timeline-out '<OUTPUT_DIR>/dialogue_timeline.md' --srt-out '<OUTPUT_DIR>/subtitles.srt'"
```

Transcript cleanup rules:
- Keep timestamps unchanged.
- Correct obvious homophones, speech-recognition typos, punctuation, sentence breaks, names, amounts, units, and repeated filler only when supported by context.
- Preserve speaker meaning, tone, order, and spoken intent.
- Keep natural spoken-language style; do not rewrite into polished ad copy.
- Mark uncertain words or lines as `[unclear]` or `[疑似：...]`.
- Ask the user to confirm any `[unclear]` lines before final prompt generation.
- Use `clean_transcript.md`, not `raw_transcript.txt`, when building `dialogue_timeline.md`.

Dialogue timeline format:

```text
00:00-00:02 Character says: "..."
Tone: excited, casual, UGC-style.
Visual sync: gesture or facial expression during this line.
```

If no ASR tool is available, ask the user for transcript or permission to continue with `[unclear]` timestamp blocks.

Ask user to confirm:
- storyboard image is the visual reference to upload into Seedance
- frame reading order: left-to-right, top-to-bottom, or custom numbered order
- cleaned dialogue/subtitle transcript is correct
- whether dialogue should be kept, rewritten, translated, or removed
- which product/object should be replaced
- which overlay/object should be removed, if any
- whether to preserve model/person
- whether to preserve hands/body pose
- whether to preserve original scene/background
- whether to preserve subtitles/CTA
- target duration
- target aspect ratio
- audio mode

Do not proceed to replacement planning or final prompt until user confirms the storyboard reference, target edit, and dialogue handling.

### Phase 5: Product Analysis

Analyze uploaded product image(s):
- product type
- shape
- color
- material
- logo/package text
- scale
- how it should be held, worn, placed, opened, applied, or displayed

If product identity or replacement mapping is unclear, ask a direct question.

### Phase 6: Replacement Plan

Generate `replacement_plan.md` using:
- shot-by-shot source product usage
- replacement product usage
- overlay/object removal instructions
- timestamped dialogue handling
- preserved elements
- changed elements
- banned changes
- CTA/subtitle changes

Ask user to confirm the replacement plan.

### Phase 7: Seedance Prompt

After confirmation, generate:
- `seedance_prompt.md`
- optional `subtitles.srt`
- optional shot prompt blocks

Prompt must include:
- storyboard image reference rule
- frame reading order
- dialogue timeline with exact timestamps and spoken lines when speech exists
- product replacement rule
- overlay/object removal rule if requested
- output duration
- output aspect ratio
- audio mode
- per-shot instructions
- negative constraints

## Output Contract

Create:
- `storyboard_grid.jpg`
- `frames/`
- `video_analysis.json`
- `video_quality.json` when enhancement is considered
- `enhanced/enhanced_reference.mp4` when enhancement runs
- `enhanced/enhancement_metadata.json` when enhancement runs
- `upscaled/upscaled_video.mp4` when final video super-resolution runs
- `upscaled/upscale_metadata.json` when final video super-resolution runs
- `shot_analysis.md`
- `raw_transcript.txt` when ASR runs
- `clean_transcript.md` when ASR runs
- `dialogue_timeline.md` when speech exists
- `product_analysis.md`
- `replacement_plan.md`
- `seedance_prompt.md`

Optional:
- `subtitles.srt`
- `jimeng-joint-mannequin/jimeng_joint_mannequin.mp4` when 2.5D white-mannequin mode runs
- `jimeng-joint-mannequin/jimeng_joint_mannequin_metadata.json` when 2.5D white-mannequin mode runs

## Default Output Settings

If user does not choose:
- duration: inherit reference video
- aspect ratio: inherit reference video
- audio: ask user; do not default to silent

## Prompting Rule

When generating `seedance_prompt.md`, write the prompt for this usage:

```text
Upload storyboard_grid.jpg to Seedance, then paste the generated prompt.
```

The prompt must say:

```text
Use the uploaded storyboard image as the primary visual reference.
Animate the storyboard frames left to right, top to bottom.
```

If speech exists, the prompt must include:

```text
Dialogue Timeline
00:00-00:02 Character says: "..."
Tone: ...
Visual sync: ...
```

The prompt must not say:

```text
Use the uploaded reference video as the reference.
```

The prompt must not:
- summarize spoken content
- omit dialogue timing when speech exists
- invent exact lines when ASR is uncertain

## Local Dry Run

Use this after the user provides a reference video:

```powershell
pwsh -NoProfile -Command "python skills/seedance-reference-product-replacer/scripts/resolve_reference_video.py --input '<VIDEO_PATH_OR_DOUYIN_SHARE_TEXT>' --out-dir 'work/seedance-run/source'"
```

Then read `work/seedance-run/source/reference_input.json` and use its `video_path`:

```powershell
pwsh -NoProfile -Command "python skills/seedance-reference-product-replacer/scripts/analyze_video.py --video '<RESOLVED_VIDEO_PATH>' --out 'work/seedance-run/video_analysis.json'"
```

```powershell
pwsh -NoProfile -Command "python skills/seedance-reference-product-replacer/scripts/extract_storyboard.py --video '<RESOLVED_VIDEO_PATH>' --out-dir 'work/seedance-run'"
```

Optional clearer storyboard path:

```powershell
pwsh -NoProfile -Command "python skills/seedance-reference-product-replacer/scripts/check_video_quality.py --video '<RESOLVED_VIDEO_PATH>' --out 'work/seedance-run/video_quality.json'"
```

```powershell
pwsh -NoProfile -Command "python skills/seedance-reference-product-replacer/scripts/enhance_video.py --video '<RESOLVED_VIDEO_PATH>' --out-dir 'work/seedance-run/enhanced' --backend auto --profile compressed --scale 2"
```

```powershell
pwsh -NoProfile -Command "python skills/seedance-reference-product-replacer/scripts/extract_storyboard.py --video 'work/seedance-run/enhanced/enhanced_reference.mp4' --out-dir 'work/seedance-run' --max-frames 24"
```

After user confirmation, create `work/seedance-run/prompt_values.json`, then run:

```powershell
pwsh -NoProfile -Command "python skills/seedance-reference-product-replacer/scripts/build_prompt_pack.py --input 'work/seedance-run/prompt_values.json' --out-dir 'work/seedance-run'"
```

Validate any final prompt independently:

```powershell
pwsh -NoProfile -Command "python skills/seedance-reference-product-replacer/scripts/lint_seedance_prompt.py --prompt 'work/seedance-run/seedance_prompt.md' --speech unknown"
```

Standalone final video upscale:

```powershell
pwsh -NoProfile -Command "python skills/seedance-reference-product-replacer/scripts/upscale_video.py --video '<FINAL_VIDEO_PATH>' --out-dir 'work/seedance-run/upscaled' --backend auto --profile compressed --scale 2 --model realesr-animevideov3 --tile 0"
```
