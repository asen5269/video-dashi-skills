# Video Enhancement and Super-Resolution

Use source enhancement only to obtain clearer analysis frames. Use final-video upscale only for a completed generated video.

## Inspect Quality

```powershell
pwsh -NoProfile -Command "python '<SKILL_ROOT>/scripts/check_video_quality.py' --video '<VIDEO_PATH>' --out '<OUTPUT_DIR>/video_quality.json'"
```

Choose a profile:

- realistic people or product footage: `realistic`
- product close-ups: `product`
- compressed platform footage: `compressed`
- game footage: `game`
- anime or cartoon footage: `anime`
- already clean 1080p+ footage: skip, or use `clean --scale 1`

## Enhance a Source

```powershell
pwsh -NoProfile -Command "python '<SKILL_ROOT>/scripts/enhance_video.py' --video '<VIDEO_PATH>' --out-dir '<OUTPUT_DIR>/enhanced' --backend auto --profile compressed --scale 2"
```

`auto` uses `realesrgan-ncnn-vulkan` when it is available on `PATH` or under `<SKILL_ROOT>/vendor/`; otherwise it uses an FFmpeg high-quality scale, mild denoise, and mild sharpening fallback.

Preserve aspect ratio, shot order, timing, motion, identity, faces, products, and style. Do not beautify, de-age, restyle, over-sharpen, or invent detail.

Before extracting the final storyboard from the enhanced source, compare its frame count, resolution ratio and per-frame timing with the original. Enhancement is not a new timing authority. If timestamps changed, extract from the original instead or explicitly map and review the frames; do not silently relabel enhanced timestamps as original timestamps.

```powershell
pwsh -NoProfile -Command "python '<SKILL_ROOT>/scripts/extract_storyboard.py' --video '<OUTPUT_DIR>/enhanced/enhanced_reference.mp4' --out-dir '<OUTPUT_DIR>' --max-frames 24"
```

Never upload `enhanced_reference.mp4` as the primary Seedance reference.

## Upscale a Completed Video

Final delivery super-resolution requires Real-ESRGAN. Do not substitute FFmpeg-only scaling.

For 720p to 1080p:

```powershell
pwsh -NoProfile -Command "python '<SKILL_ROOT>/scripts/upscale_video.py' --video '<FINAL_VIDEO_PATH>' --out-dir '<OUTPUT_DIR>/upscaled' --scale 2 --target-height 1080 --model realesr-animevideov3 --tile 0"
```

For vertical 720x1280 to 1440x2560, omit `--target-height` and retain `--scale 2`.

Use `realesr-animevideov3` by default for AI-generated video. Do not use `realesrgan-x4plus` or `realesrgan-x4plus-anime` unless the user explicitly requests them because they may create block or grid artifacts.

Verify `upscaled_video.mp4` and `upscale_metadata.json` with FFprobe before delivery.
