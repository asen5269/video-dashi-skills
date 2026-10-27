# Transcript, Replacement, and Prompt Workflow

Use this reference when the source contains speech or when producing a replacement plan and final Seedance prompt.

For a supplied storyboard without video, skip ASR. Do not invent spoken lines or timing from visible subtitles; put missing decisions in the consolidated review plan.

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

ASR timestamps are segment estimates, not verified word alignment. Listen and review segment timing against the video. If requested precision exceeds that, use an available forced-aligner or manual timing review and report remaining uncertainty. Preserve original raw files and source time origin; an output duration change requires an explicitly reviewed dialogue and shot retiming plan.

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

Present this complete plan for one consolidated confirmation, including dialogue uncertainties, actual reference mode/order, duration, audio and every upload asset. Do not ask for a separate product-plan confirmation after this same plan was already approved. Product analysis may be skipped when `replacement_target` is `none`.

## Prompt Values

Create `<OUTPUT_DIR>/prompt_values.json` with values used by the templates:

```json
{
  "confirmed": false,
  "unresolved_decisions": "Pending review.",
  "reference_mode": "storyboard",
  "frame_order": "left to right, top to bottom",
  "duration_seconds": 8,
  "assets": [
    {"id": "image_1", "role": "storyboard", "path": "<ABSOLUTE_STORYBOARD_PATH>"},
    {"id": "image_2", "role": "product", "path": "<ABSOLUTE_PRODUCT_PATH>"}
  ],
  "shots": [
    {"id": "S1", "start": 0, "end": 8, "prompt": "Reference image_1; replace the confirmed object using image_2."}
  ],
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
  "speech": "no"
}
```

`duration_seconds` is authoritative; the generator derives the displayed duration from it. Use finite numeric output seconds in `shots`; intervals must cover the entire output with no gaps or overlaps (50ms tolerance for rounding). Each shot must name its primary reference asset ID; each product asset must be mapped to at least one shot. Use `shot_mapping` to record source intervals separately when output timing changes. The generator renders shot prompts from `shots`; legacy free-text `shot_prompts` is not authoritative for final generation. Asset validation checks existence and mapping, not the semantic identity of the pictured product; inspect the files visually.

For video reference use `reference_mode=video` and exactly one `role=video` asset with an existing absolute video path. For no replacement use `replacement_target=none` and omit product assets. In image-only workflows, confirm output timing, ratio and audio; do not substitute the grid's canvas ratio. Resolve speech to `yes` or `no` after review.

Build the review plan only (this does not create or overwrite a final prompt):

```powershell
pwsh -NoProfile -Command "python '<SKILL_ROOT>/scripts/build_prompt_pack.py' --input '<OUTPUT_DIR>/prompt_values.json' --out-dir '<OUTPUT_DIR>' --stage plan"
```

Set `confirmed=true` only after the complete plan is approved; clear `unresolved_decisions` to `None.` once every listed question is resolved. Then generate the final prompt:

```powershell
pwsh -NoProfile -Command "python '<SKILL_ROOT>/scripts/build_prompt_pack.py' --input '<OUTPUT_DIR>/prompt_values.json' --out-dir '<OUTPUT_DIR>' --stage final"
```

The final stage rejects incomplete values and validates before writing. A preexisting final prompt in the same directory may be stale after a failed attempt; never deliver it as the new result. Use a fresh output directory for a new revision. Confirmation is recorded by the agent from actual conversation; the boolean alone does not establish consent.

The prompt must:

- identify the selected primary reference mode and every uploaded asset by ID
- animate frames in the confirmed order
- preserve shot order, pose progression, composition, lighting, camera, continuity, and edit rhythm
- include exact dialogue lines and timestamps when speech exists
- identify the single confirmed replacement target
- include duration, aspect ratio, audio mode, per-shot instructions, and negative constraints

In storyboard mode, do not instruct use of video as primary reference. In explicit video-to-video mode, use the confirmed uploaded video for motion/timing. Do not promise exact reconstruction of motion from static frames, or perfect preservation of faces, hands, logos, text or dialogue sync.
