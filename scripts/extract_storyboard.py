import argparse
import math
import subprocess
from pathlib import Path


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def probe_duration(video_path: str) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            video_path,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def effective_fps(video_path: str, fps: float, max_frames: int) -> float:
    duration = probe_duration(video_path)
    if duration <= 0 or max_frames <= 0:
        return fps
    return min(fps, max_frames / duration)


def extract_frames(video_path: str, frames_dir: Path, fps: float, width: int, max_frames: int) -> list[Path]:
    frames_dir.mkdir(parents=True, exist_ok=True)
    for stale_frame in frames_dir.glob("frame_*.jpg"):
        stale_frame.unlink()

    output_pattern = str(frames_dir / "frame_%03d.jpg")
    sample_fps = effective_fps(video_path, fps, max_frames)
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            video_path,
            "-vf",
            f"fps={sample_fps},scale={width}:-1",
            "-frames:v",
            str(max_frames),
            "-q:v",
            "2",
            output_pattern,
        ]
    )
    return sorted(frames_dir.glob("frame_*.jpg"))


def build_grid(frames: list[Path], output_path: Path, columns: int) -> None:
    if not frames:
        raise SystemExit("no frames extracted")

    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise SystemExit("Pillow is required: python -m pip install pillow") from exc

    images = [Image.open(frame).convert("RGB") for frame in frames]
    cell_width = max(image.width for image in images)
    cell_height = max(image.height for image in images) + 24
    rows = math.ceil(len(images) / columns)
    grid = Image.new("RGB", (cell_width * columns, cell_height * rows), "white")
    draw = ImageDraw.Draw(grid)
    font = ImageFont.load_default()

    for index, image in enumerate(images):
        row = index // columns
        column = index % columns
        x = column * cell_width
        y = row * cell_height
        grid.paste(image, (x, y))
        draw.text((x + 6, y + image.height + 5), f"Shot {index + 1}", fill=(0, 0, 0), font=font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    grid.save(output_path, quality=92)

    for image in images:
        image.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--fps", type=float, default=1.0)
    parser.add_argument("--width", type=int, default=360)
    parser.add_argument("--columns", type=int, default=4)
    parser.add_argument("--max-frames", type=int, default=24)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    frames = extract_frames(args.video, out_dir / "frames", args.fps, args.width, args.max_frames)
    build_grid(frames, out_dir / "storyboard_grid.jpg", args.columns)


if __name__ == "__main__":
    main()
