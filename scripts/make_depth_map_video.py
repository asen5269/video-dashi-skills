import argparse
import json
import statistics
import subprocess
from pathlib import Path

try:
    from .extract_storyboard import probe_timestamps
except ImportError:
    from extract_storyboard import probe_timestamps


MODEL_ID = "depth-anything/Depth-Anything-V2-Small-hf"


def timing_info(video: Path) -> dict:
    times, duration = probe_timestamps(str(video))
    intervals = [end - start for start, end in zip(times, times[1:])]
    nominal = statistics.median(intervals) if intervals else duration
    return {"frame_count": len(times), "video_duration": duration,
            "variable_frame_rate": any(abs(value - nominal) > max(0.00001, nominal * 0.01)
                                       for value in intervals)}


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def video_info(path: Path) -> dict:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-count_frames",
            "-show_entries", "stream=codec_type,codec_name,width,height,r_frame_rate,nb_read_frames",
            "-show_entries", "format=duration,size", "-of", "json", str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(result.stdout)


def render(
    video: Path,
    work: Path,
    invert: bool,
    batch_size: int,
    smoothing_alpha: float,
    face_contrast: float,
    local_contrast: float,
) -> int:
    import cv2
    import numpy as np
    import torch
    from PIL import Image
    from transformers import AutoImageProcessor, AutoModelForDepthEstimation

    device = "cuda" if torch.cuda.is_available() else "cpu"
    processor = AutoImageProcessor.from_pretrained(MODEL_ID)
    model = AutoModelForDepthEstimation.from_pretrained(MODEL_ID).to(device).eval()

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise SystemExit(f"cannot open video: {video}")
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    writer = cv2.VideoWriter(
        str(work), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height), False
    )
    if not writer.isOpened():
        raise SystemExit(f"cannot create video: {work}")

    frames = []
    rendered = 0
    low_smooth = None
    high_smooth = None
    face_detector = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    def process(batch: list[np.ndarray]) -> None:
        nonlocal rendered, low_smooth, high_smooth
        images = [
            Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)) for frame in batch
        ]
        inputs = processor(images=images, return_tensors="pt")
        pixels = inputs["pixel_values"].to(device)
        with torch.autocast(device_type=device, enabled=device == "cuda"):
            depths = model(pixel_values=pixels).predicted_depth
        depths = torch.nn.functional.interpolate(
            depths.unsqueeze(1),
            size=(height, width),
            mode="bicubic",
            align_corners=False,
        )[:, 0].float().cpu().numpy()
        for depth, source_frame in zip(depths, batch):
            low, high = np.percentile(depth, (2, 98))
            if low_smooth is None:
                low_smooth, high_smooth = low, high
            else:
                low_smooth = (1.0 - smoothing_alpha) * low_smooth + smoothing_alpha * low
                high_smooth = (1.0 - smoothing_alpha) * high_smooth + smoothing_alpha * high
            gray = np.clip(
                (depth - low_smooth) / max(high_smooth - low_smooth, 1e-6), 0, 1
            )
            if face_contrast > 1.0 and not face_detector.empty():
                source_gray = cv2.cvtColor(source_frame, cv2.COLOR_BGR2GRAY)
                faces = face_detector.detectMultiScale(
                    source_gray, scaleFactor=1.1, minNeighbors=4, minSize=(40, 40)
                )
                for x, y, w, h in faces:
                    pad_x, pad_y = int(w * 0.18), int(h * 0.18)
                    x0, y0 = max(0, x - pad_x), max(0, y - pad_y)
                    x1, y1 = min(width, x + w + pad_x), min(height, y + h + pad_y)
                    roi = gray[y0:y1, x0:x1]
                    center = float(np.median(roi))
                    gray[y0:y1, x0:x1] = np.clip(
                        center + (roi - center) * face_contrast, 0, 1
                    )
            if invert:
                gray = 1.0 - gray
            if local_contrast > 0:
                clahe = cv2.createCLAHE(
                    clipLimit=local_contrast, tileGridSize=(8, 8)
                )
                gray = clahe.apply((gray * 255).astype(np.uint8)).astype(np.float32) / 255.0
            writer.write((gray * 255).astype(np.uint8))
            rendered += 1

    with torch.inference_mode():
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frames.append(frame)
            if len(frames) == batch_size:
                process(frames)
                frames.clear()
        if frames:
            process(frames)

    cap.release()
    writer.release()
    if rendered == 0:
        raise SystemExit("no frames rendered")
    return rendered


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--invert", action="store_true")
    parser.add_argument("--keep-audio", action="store_true")
    parser.add_argument("--allow-cfr-retiming", action="store_true",
                        help="Explicitly allow VFR input to be retimed at fixed fps")
    parser.add_argument("--batch-size", type=int, default=0)
    parser.add_argument("--crf", type=int, default=18)
    parser.add_argument("--preset", default="medium")
    parser.add_argument("--smoothing-alpha", type=float, default=0.08)
    parser.add_argument("--face-contrast", type=float, default=1.0)
    parser.add_argument("--local-contrast", type=float, default=0.0)
    args = parser.parse_args()

    video = Path(args.video).resolve()
    timing = timing_info(video)
    if timing["variable_frame_rate"] and not args.allow_cfr_retiming:
        raise SystemExit("Variable-frame-rate input requires --allow-cfr-retiming; original timestamps cannot be kept.")
    import torch

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    work = out_dir / "_depth_bw_work.mp4"
    output = out_dir / "depth_bw.mp4"
    batch_size = args.batch_size or (8 if torch.cuda.is_available() else 1)

    rendered = render(
        video,
        work,
        args.invert,
        batch_size,
        args.smoothing_alpha,
        args.face_contrast,
        args.local_contrast,
    )
    command = ["ffmpeg", "-y", "-v", "error", "-i", str(work)]
    if args.keep_audio:
        command += ["-i", str(video), "-map", "0:v:0", "-map", "1:a?"]
    else:
        command += ["-map", "0:v:0", "-an"]
    command += [
        "-c:v", "libx264", "-preset", args.preset, "-crf", str(args.crf),
        "-pix_fmt", "yuv420p",
    ]
    if args.keep_audio:
        command += ["-c:a", "copy"]
    command += ["-movflags", "+faststart", str(output)]
    run(command)
    work.unlink(missing_ok=True)

    before, after = video_info(video), video_info(output)
    source_stream = next(stream for stream in before["streams"] if stream["codec_type"] == "video")
    output_stream = next(stream for stream in after["streams"] if stream["codec_type"] == "video")
    output_count = int(output_stream["nb_read_frames"])
    if rendered != timing["frame_count"] or output_count != rendered:
        raise SystemExit("Depth output frame count mismatch; output is not verified.")
    if any(source_stream[key] != output_stream[key] for key in ["width", "height"]):
        raise SystemExit("Depth output dimensions mismatch; output is not verified.")
    metadata = {
        "input_video": str(video),
        "output_video": str(output),
        "model": MODEL_ID,
        "depth_type": "monocular relative depth",
        "mapping": "near=black, far=white" if args.invert else "near=white, far=black",
        "temporal_normalization": f"2nd/98th percentiles, exponential smoothing alpha={args.smoothing_alpha}",
        "face_contrast": args.face_contrast,
        "local_contrast": args.local_contrast,
        "audio_preserved": bool(args.keep_audio),
        "rendered_frames": rendered,
        "source_timing": timing,
        "timing_mode": "fixed fps; original VFR timestamps are not preserved",
        "cfr_retiming_authorized": args.allow_cfr_retiming,
        "container_duration_delta": float(after["format"]["duration"]) - float(before["format"]["duration"]),
        "before": before,
        "after": after,
    }
    (out_dir / "depth_map_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(output)


if __name__ == "__main__":
    main()
