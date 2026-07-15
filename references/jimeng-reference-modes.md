# Jimeng Review-Friendly Reference Modes

Use these modes to create non-photorealistic motion references, not to evade moderation. Preserve source ratio, duration, fps, frame order, blocking, choreography, and visible body motion.

Before processing, inspect representative frames for realistic identity details, unlicensed audio, third-party watermarks, logos, subtitles, copyrighted characters, and branded elements.

Remove audio by default. Use `--keep-audio` only after the user confirms authorization. Remove a watermark only after measuring a confirmed normalized `x,y,w,h` rectangle.

## Flat Animation

Use for `即梦审核友好版` or a four-tone non-photorealistic action reference:

```powershell
pwsh -NoProfile -Command "python '<SKILL_ROOT>/scripts/make_jimeng_review_friendly.py' --video '<VIDEO_PATH>' --out-dir '<OUTPUT_DIR>/jimeng-review'"
```

Optional verified watermark rectangle:

```powershell
pwsh -NoProfile -Command "python '<SKILL_ROOT>/scripts/make_jimeng_review_friendly.py' --video '<VIDEO_PATH>' --out-dir '<OUTPUT_DIR>/jimeng-review' --watermark-rect '0.43,0.89,0.16,0.11'"
```

Outputs:

- `jimeng-review/jimeng_review_friendly.mp4`
- `jimeng-review/jimeng_review_metadata.json`

## Person Mask

Use for `人物自动遮罩`, `自动打码`, or `描边人物` while preserving the source background:

```powershell
pwsh -NoProfile -Command "python '<SKILL_ROOT>/scripts/make_jimeng_person_mask.py' --video '<VIDEO_PATH>' --out-dir '<OUTPUT_DIR>/jimeng-person-mask'"
```

Defaults:

- mode: hybrid
- detector: `yolo11s-seg.pt`
- SAM: `sam2.1_t.pt`
- redetection interval: 24 frames
- detector size: 1280
- SAM size: 1024
- fill: purple vertical gradient
- outline: 1px white

Use interval 12 for cuts or fast motion, 24 normally, and 48 for slow footage with limited GPU memory. Hybrid mode periodically detects people and propagates masks with SAM 2. If SAM 2 VOS is unavailable, the script falls back to per-frame refinement. CUDA is required by default; `--allow-cpu` is extremely slow.

Outputs:

- `jimeng-person-mask/jimeng_person_mask.mp4`
- `jimeng-person-mask/jimeng_person_mask_metadata.json`

## Articulated 2.5D Mannequin

Use for `白模绿幕`, `关节白模`, `骨骼白模`, or `2.5D动作参考`:

```powershell
pwsh -NoProfile -Command "python '<SKILL_ROOT>/scripts/make_jimeng_joint_mannequin.py' --video '<VIDEO_PATH>' --out-dir '<OUTPUT_DIR>/jimeng-joint-mannequin'"
```

The pipeline uses YOLO11 Pose, BoT-SORT track IDs, temporal joint smoothing, limb capsules, and a chroma-green `#00ff00` background. Use `--smooth-alpha 0.8` for fast motion and `0.5` for steadier motion.

Outputs:

- `jimeng-joint-mannequin/jimeng_joint_mannequin.mp4`
- `jimeng-joint-mannequin/jimeng_joint_mannequin_metadata.json`

## Limitations

- Heavy blur, full occlusion, and touching people can merge masks or lose limbs.
- Hidden body boundaries cannot be reconstructed reliably.
- Multi-person tracking can swap IDs during severe overlap.
- The mannequin is a 2.5D representation, not a recovered SMPL or other 3D mesh.
- Use manual keyframes or professional rotoscoping when reference-grade contours are required.

Report every transformation and state that platform approval is not guaranteed.
