# Monochrome Depth-Map Video

Use for `深度黑白视频`, `黑白深度图`, `depth map video`, or `monochrome depth video`.

## Meaning

- Default: near surfaces are white, far surfaces are black.
- Use `--invert` only when the user requests near=black and far=white.
- This is monocular relative-depth estimation, not metric distance. Do not claim centimeter accuracy or recovered 3D geometry.

## Preservation Rules

- Preserve width, height, decoded frame count, frame order and aspect ratio. The current encoder writes fixed fps; default processing rejects detected variable-frame-rate input before model loading. Do not claim timestamp preservation.
- For VFR input, explain that retiming can change motion timing and audio sync. Use `--allow-cfr-retiming` only after the user explicitly approves that change. If original VFR timestamps are required, stop this branch and report that the bundled encoder cannot meet the requirement.
- Apply temporally smoothed percentile normalization to reduce brightness flicker.
- Do not crop, mirror, interpolate, stabilize, remove overlays, or alter timing unless requested.
- Depth-map reference output is silent by default. Use `--keep-audio` only after the user confirms the audio may be retained.

## Command

```powershell
pwsh -NoProfile -Command "python '<SKILL_ROOT>/scripts/make_depth_map_video.py' --video '<VIDEO_PATH>' --out-dir '<OUTPUT_DIR>/depth-map'"
```

Invert depth polarity:

```powershell
pwsh -NoProfile -Command "python '<SKILL_ROOT>/scripts/make_depth_map_video.py' --video '<VIDEO_PATH>' --out-dir '<OUTPUT_DIR>/depth-map' --invert"
```

The script uses `depth-anything/Depth-Anything-V2-Small-hf`. Required Python packages are `torch`, `transformers`, `opencv-python`, `Pillow`, and `numpy`; FFmpeg and FFprobe must be available.

## Outputs

- `depth-map/depth_bw.mp4`
- `depth-map/depth_map_metadata.json`

## Verification

Use FFprobe to compare source and output duration, resolution, fps, and frame count. Confirm output has one H.264 grayscale video stream and no audio unless `--keep-audio` was explicitly selected. Inspect a representative frame to confirm expected near/far polarity.
Inspect `source_timing`, `timing_mode` and `container_duration_delta` in the metadata. A duration delta within one source frame is a rounding tolerance for CFR, not a promise of exact timestamp identity. Check video-stream timing separately if retained audio extends container duration. VFR detection uses decoded timestamp intervals with a 1%/10µs tolerance; borderline jitter still needs review.
