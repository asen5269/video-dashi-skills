import argparse
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def video_info(path: Path) -> dict:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-count_frames",
            "-show_entries", "stream=codec_type,width,height,r_frame_rate,nb_read_frames",
            "-show_entries", "format=duration,size", "-of", "json", str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(result.stdout)


def parse_rect(value: str | None) -> tuple[float, float, float, float] | None:
    if not value:
        return None
    parts = tuple(float(x) for x in value.split(","))
    if len(parts) != 4 or any(x < 0 or x > 1 for x in parts):
        raise argparse.ArgumentTypeError("watermark rect must be normalized x,y,w,h values from 0 to 1")
    x, y, w, h = parts
    if x + w > 1 or y + h > 1:
        raise argparse.ArgumentTypeError("watermark rect exceeds frame bounds")
    return parts


def render(video: Path, silent_out: Path, watermark_rect: tuple[float, float, float, float] | None) -> None:
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise SystemExit(f"cannot open video: {video}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    writer = cv2.VideoWriter(str(silent_out), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    if not writer.isOpened():
        raise SystemExit(f"cannot create video: {silent_out}")

    watermark_mask = None
    if watermark_rect:
        x, y, w, h = watermark_rect
        watermark_mask = np.zeros((height, width), np.uint8)
        cv2.rectangle(
            watermark_mask,
            (int(x * width), int(y * height)),
            (int((x + w) * width), int((y + h) * height)),
            255,
            -1,
        )

    # Flat limited palette removes photorealistic face texture while preserving pose and motion silhouettes.
    palette = np.array(
        [[30, 28, 26], [92, 71, 55], [169, 137, 98], [226, 215, 188], [247, 242, 225]],
        np.uint8,
    )
    kernel = np.ones((2, 2), np.uint8)
    frames = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if watermark_mask is not None:
            frame = cv2.inpaint(frame, watermark_mask, 5, cv2.INPAINT_TELEA)
        softened = cv2.GaussianBlur(frame, (13, 13), 0)
        gray = cv2.cvtColor(softened, cv2.COLOR_BGR2GRAY)
        output = palette[np.clip(gray // 52, 0, 4)]
        edges = cv2.Canny(gray, 55, 135)
        edges = cv2.dilate(edges, kernel, iterations=1)
        output[edges > 0] = (18, 18, 18)
        writer.write(output)
        frames += 1
    cap.release()
    writer.release()
    if frames == 0:
        raise SystemExit("no frames rendered")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--watermark-rect", help="normalized x,y,w,h; inspect frames before setting")
    parser.add_argument("--keep-audio", action="store_true", help="use only when the audio is confirmed authorized")
    parser.add_argument("--crf", type=int, default=22)
    parser.add_argument("--preset", default="slow")
    args = parser.parse_args()

    video = Path(args.video).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    silent_work = out_dir / "_review_friendly_silent_work.mp4"
    output = out_dir / "jimeng_review_friendly.mp4"
    rect = parse_rect(args.watermark_rect)

    render(video, silent_work, rect)
    if args.keep_audio:
        command = [
            "ffmpeg", "-y", "-i", str(silent_work), "-i", str(video),
            "-map", "0:v:0", "-map", "1:a?", "-c:v", "libx264", "-preset", args.preset,
            "-crf", str(args.crf), "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart",
        ]
    else:
        command = [
            "ffmpeg", "-y", "-i", str(silent_work), "-map", "0:v:0", "-an",
            "-c:v", "libx264", "-preset", args.preset, "-crf", str(args.crf),
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        ]
    command.append(str(output))
    run(command)
    silent_work.unlink(missing_ok=True)

    metadata = {
        "input_video": str(video),
        "output_video": str(output),
        "style": "non-photorealistic four-tone motion reference",
        "audio_preserved": bool(args.keep_audio),
        "watermark_rect": rect,
        "before": video_info(video),
        "after": video_info(output),
        "review_note": "Compliance-oriented preprocessing only; platform approval is not guaranteed.",
    }
    (out_dir / "jimeng_review_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(output)


if __name__ == "__main__":
    main()
