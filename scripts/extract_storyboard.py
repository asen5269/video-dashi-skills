import argparse
import bisect
import json
import math
import re
import subprocess
from pathlib import Path


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def probe_timestamps(video_path: str) -> tuple[list[float], float]:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_frames",
         "-show_entries", "frame=best_effort_timestamp_time,pkt_duration_time,duration_time",
         "-of", "json", video_path], check=True, capture_output=True, text=True,
    )
    frames = json.loads(result.stdout)["frames"]
    times = [float(frame["best_effort_timestamp_time"]) for frame in frames]
    if not times or times != sorted(times) or len(set(times)) != len(times):
        raise SystemExit("Source needs strictly increasing presentation timestamps.")
    origin = times[0]
    times = [time - origin for time in times]
    last = frames[-1]
    step = float(last.get("duration_time") or last.get("pkt_duration_time") or 0)
    if step <= 0:
        step = times[-1] - times[-2] if len(times) > 1 else 1 / 25
    return times, times[-1] + step


def detect_cuts(video_path: str, threshold: float) -> list[float]:
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", video_path, "-an", "-vf",
         f"setpts=PTS-STARTPTS,scale=320:-1,select='gt(scene,{threshold})',showinfo",
         "-f", "null", "-"], check=True, capture_output=True, text=True,
    )
    return [float(value) for value in re.findall(r"pts_time:([\d.eE+-]+)", result.stderr)]


def select_frames(times: list[float], duration: float, cuts: list[float],
                  max_frames: int, fps: float) -> tuple[list[dict], list[dict]]:
    boundaries = [0.0] + sorted({cut for cut in cuts if 0 < cut < duration}) + [duration]
    shots = []
    selected = set()
    for index, (start, end) in enumerate(zip(boundaries, boundaries[1:]), 1):
        first, stop = bisect.bisect_left(times, start), bisect.bisect_left(times, end)
        if first == stop:
            continue
        middle = min(stop - 1, max(first, bisect.bisect_left(times, (start + end) / 2)))
        shots.append({"shot_id": index, "start": start, "end": end, "first": first, "stop": stop})
        selected.add(middle)
    if len(selected) > max_frames:
        raise SystemExit(f"Detected {len(selected)} shots; increase --max-frames above {max_frames}.")
    target = min(max_frames, len(times), max(len(selected), math.ceil(duration * fps)))
    while len(selected) < target:
        gaps = []
        for shot in shots:
            anchors = [shot["first"] - 1] + sorted(
                item for item in selected if shot["first"] <= item < shot["stop"]
            ) + [shot["stop"]]
            for left, right in zip(anchors, anchors[1:]):
                if right - left > 1:
                    candidate = (left + right) // 2
                    gaps.append((times[min(right, len(times) - 1)] - times[max(left, 0)], candidate))
        if not gaps:
            break
        selected.add(max(gaps)[1])
    entries = []
    for index in sorted(selected):
        shot = next(shot for shot in shots if shot["first"] <= index < shot["stop"])
        entries.append({"frame": f"frame_{len(entries) + 1:03d}.jpg", "source_frame_index": index,
                        "timestamp": times[index], "shot_id": shot["shot_id"]})
    return entries, [{key: value for key, value in shot.items() if key not in {"first", "stop"}}
                     for shot in shots]


def extract_frames(video_path: str, frames_dir: Path, entries: list[dict], width: int) -> list[Path]:
    frames_dir.mkdir(parents=True, exist_ok=True)
    for stale_frame in frames_dir.glob("frame_*.jpg"):
        stale_frame.unlink()

    selection = "+".join(f"eq(n\\,{entry['source_frame_index']})" for entry in entries)
    run(["ffmpeg", "-v", "error", "-y", "-i", video_path, "-vf",
         f"select={selection},scale={width}:-1", "-frames:v", str(len(entries)),
         "-fps_mode", "vfr", "-q:v", "2", str(frames_dir / "frame_%03d.jpg")])
    return [frames_dir / entry["frame"] for entry in entries]


def build_grid(frames: list[Path], output_path: Path, columns: int, entries: list[dict]) -> None:
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
        entry = entries[index]
        label = f"F{index + 1} | S{entry['shot_id']} | {entry['timestamp']:.3f}s"
        draw.text((x + 6, y + image.height + 5), label, fill=(0, 0, 0), font=font)

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
    parser.add_argument("--scene-threshold", type=float, default=0.3)
    args = parser.parse_args()
    if min(args.fps, args.width, args.columns, args.max_frames) <= 0 or not 0 < args.scene_threshold < 1:
        parser.error("Sizes and density must be positive; scene threshold must be between 0 and 1.")
    times, duration = probe_timestamps(args.video)
    cuts = detect_cuts(args.video, args.scene_threshold)
    entries, shots = select_frames(times, duration, cuts, args.max_frames, args.fps)
    out_dir = Path(args.out_dir).resolve()
    frames = extract_frames(args.video, out_dir / "frames", entries, args.width)
    build_grid(frames, out_dir / "storyboard_grid.jpg", args.columns, entries)
    manifest = {"source": str(Path(args.video).resolve()), "duration": duration,
                "time_origin": "first video frame", "frame_order": "left to right, top to bottom",
                "scene_threshold": args.scene_threshold, "shots": shots, "frames": entries,
                "limitations": "Automatic cut candidates need visual review; sampled frames do not encode motion."}
    (out_dir / "storyboard_timeline.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
