# Transcript, Replacement, and Prompt Workflow

Use this reference when the source contains speech or when producing a replacement plan and final Seedance prompt.

## Transcript Workflow

Run ASR:

```powershell
pwsh -NoProfile -Command "python '<SKILL_ROOT>/scripts/transcribe_audio.py' --video '<RESOLVED_VIDEO_PATH>' --out '<OUTPUT_DIR>/raw_transcript.txt' --srt-out '<OUTPUT_DIR>/raw_subtitles.srt'"
```

Create the cleanup scaffold:

```powershell
pwsh -NoProfile -Command "python '<SKILL_ROOT>/scripts/clean_transcript.py' --input '<OUTPUT_DIR>/raw_transcript.txt' --clean-out '<OUTPUT_DIR>/clean_transcript.md' --timeline-out '<OUTPUT_DIR>/dialogue_timeline.md' --srt-out '<OUTPUT_DIR>/subtitles.srt'"
```

Edit `clean_transcript.md` using these rules:

- Keep timestamps unchanged.
- Preserve meaning, tone, order, and spoken-language style.
- Correct clear ASR homophones, punctuation, sentence breaks, names, amounts, and units only when context supports the correction.
- Do not summarize or rewrite into polished ad copy.
- Mark uncertainty as `[unclear]` or `[疑似：...]`.
- Ask the user to confirm uncertain content before prompt generation.

Regenerate the timeline and subtitles from the cleaned transcript:

```powershell
pwsh -NoProfile -Command "python '<SKILL_ROOT>/scripts/clean_transcript.py' --input '<OUTPUT_DIR>/clean_transcript.md' --timeline-out '<OUTPUT_DIR>/dialogue_timeline.md' --srt-out '<OUTPUT_DIR>/subtitles.srt'"
```

Use exact timestamped dialogue:

```text
00:00-00:02 Character says: "..."
Tone: excited, casual, UGC-style.
Visual sync: gesture or facial expression during this line.
```

## Product Analysis

Record:

- product type, geometry, color, material, texture, logo, and package text
- approximate scale relative to hands, body, and scene objects
- how the product is held, worn, placed, opened, applied, or displayed
- shot-specific visibility and occlusion

Ask a direct question if the product identity or source-to-target mapping is unclear.

## Replacement Plan

Create a shot-by-shot plan containing:

- source and replacement product usage
- timestamped dialogue handling
- elements to preserve
- elements to change
- prohibited changes
- overlay, subtitle, and CTA instructions

Ask the user to confirm the plan before final prompt generation.

## Prompt Values

Create `<OUTPUT_DIR>/prompt_values.json` with values used by the templates:

```json
{
  "storyboard_image": "<OUTPUT_DIR>/storyboard_grid.jpg",
  "replacement_target": "object to replace",
  "duration": "inherit source or confirmed value",
  "aspect_ratio": "inherit source or confirmed value",
  "audio_mode": "preserve, rewrite, translate, or remove",
  "style": "confirmed visual style",
  "preserve_rules": "multiline rules",
  "change_rules": "multiline rules",
  "dialogue_timeline": "exact timestamped lines or no speech",
  "negative_rules": "multiline constraints",
  "shot_prompts": "shot-by-shot instructions",
  "video_path": "resolved source path",
  "source_duration": "source duration",
  "source_aspect_ratio": "source ratio",
  "source_audio": "source audio summary",
  "new_product": "replacement product description",
  "shot_mapping": "shot-by-shot mapping",
  "speech": "yes, no, or unknown"
}
```

Build the plan and prompt:

```powershell
pwsh -NoProfile -Command "python '<SKILL_ROOT>/scripts/build_prompt_pack.py' --input '<OUTPUT_DIR>/prompt_values.json' --out-dir '<OUTPUT_DIR>'"
```

The prompt must:

- state that the uploaded storyboard image is the primary visual reference
- animate frames in the confirmed order
- preserve shot order, pose progression, composition, lighting, camera, continuity, and edit rhythm
- include exact dialogue lines and timestamps when speech exists
- identify the single confirmed replacement target
- include duration, aspect ratio, audio mode, per-shot instructions, and negative constraints

The prompt must not tell Seedance to use the original or enhanced video as its primary reference.
