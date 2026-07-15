import argparse
import json
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def find_executable(*names: str) -> str | None:
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    skill_root = Path(__file__).resolve().parents[1]
    for name in names:
        for path in (skill_root / "vendor").rglob(name):
            if path.is_file():
                return str(path)
    return None


def parse_fps(value: str) -> float:
    if not value or value == "0/0":
        return 0.0
    return float(Fraction(value))


def run_ffprobe(video_path: str) -> dict:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_streams",
            "-show_format",
            video_path,
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return json.loads(result.stdout)


def video_info(video_path: str) -> dict:
    probe = run_ffprobe(video_path)
    streams = probe.get("streams", [])
    video = next(stream for stream in streams if stream.get("codec_type") == "video")
    audio = [stream for stream in streams if stream.get("codec_type") == "audio"]
    width = int(video["width"])
    height = int(video["height"])
    fps = parse_fps(video.get("avg_frame_rate") or video.get("r_frame_rate") or "0/0")
    duration = float(video.get("duration") or probe.get("format", {}).get("duration") or 0)
    return {
        "width": width,
        "height": height,
        "fps": round(fps, 3),
        "duration_seconds": round(duration, 3),
        "has_audio": bool(audio),
    }


def ffmpeg_filter(profile: str, scale: int) -> str:
    scale_filter = f"scale=iw*{scale}:ih*{scale}:flags=lanczos"
    profiles = {
        "realistic": f"hqdn3d=1.2:1.2:4:4,{scale_filter},unsharp=5:5:0.35:3:3:0.15",
        "product": f"hqdn3d=1.0:1.0:3:3,{scale_filter},unsharp=5:5:0.45:3:3:0.18",
        "compressed": f"hqdn3d=2.0:1.5:6:5,{scale_filter},unsharp=5:5:0.30:3:3:0.12",
        "game": f"{scale_filter},unsharp=5:5:0.50:3:3:0.20",
        "anime": f"{scale_filter},unsharp=3:3:0.40:3:3:0.15",
        "clean": scale_filter,
    }
    return profiles.get(profile, profiles["realistic"])


def resolve_backend(requested: str) -> str:
    if requested != "auto":
        return requested
    if find_executable("realesrgan-ncnn-vulkan", "realesrgan-ncnn-vulkan.exe"):
        return "realesrgan"
    return "ffmpeg"


def enhance_with_ffmpeg(video: str, out_path: Path, profile: str, scale: int, crf: int, preset: str) -> None:
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            video,
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-vf",
            ffmpeg_filter(profile, scale),
            "-c:v",
            "libx264",
            "-crf",
            str(crf),
            "-preset",
            preset,
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "copy",
            str(out_path),
        ]
    )


def enhance_with_realesrgan(video: str, out_dir: Path, out_path: Path, model: str, scale: int, crf: int, preset: str, tile: int = 0) -> None:
    executable = find_executable("realesrgan-ncnn-vulkan", "realesrgan-ncnn-vulkan.exe")
    if not executable:
        raise SystemExit("realesrgan-ncnn-vulkan not found")

    info = video_info(video)
    fps = str(info["fps"] or 30)
    frames_dir = out_dir / "frames_raw"
    upscaled_dir = out_dir / "frames_upscaled"
    shutil.rmtree(frames_dir, ignore_errors=True)
    shutil.rmtree(upscaled_dir, ignore_errors=True)
    frames_dir.mkdir(parents=True, exist_ok=True)
    upscaled_dir.mkdir(parents=True, exist_ok=True)

    run(["ffmpeg", "-y", "-i", video, "-vsync", "0", str(frames_dir / "frame_%08d.png")])
    command = [executable, "-i", str(frames_dir), "-o", str(upscaled_dir), "-n", model, "-s", str(scale), "-t", str(tile), "-f", "png"]
    models_dir = Path(executable).parent / "models"
    if models_dir.exists():
        command.extend(["-m", str(models_dir)])
    run(command)
    run(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            fps,
            "-i",
            str(upscaled_dir / "frame_%08d.png"),
            "-i",
            video,
            "-map",
            "0:v:0",
            "-map",
            "1:a?",
            "-c:v",
            "libx264",
            "-crf",
            str(crf),
            "-preset",
            preset,
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "copy",
            "-shortest",
            str(out_path),
        ]
    )


def write_metadata(out_dir: Path, metadata: dict) -> None:
    (out_dir / "enhancement_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--backend", choices=["auto", "ffmpeg", "realesrgan"], default="auto")
    parser.add_argument("--profile", choices=["realistic", "product", "compressed", "game", "anime", "clean"], default="realistic")
    parser.add_argument("--scale", type=int, choices=[1, 2, 3, 4], default=2)
    parser.add_argument("--model", default="realesrgan-x4plus")
    parser.add_argument("--crf", type=int, default=16)
    parser.add_argument("--preset", default="slow")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "enhanced_reference.mp4"
    backend = resolve_backend(args.backend)
    before = video_info(args.video)

    if backend == "realesrgan":
        enhance_with_realesrgan(args.video, out_dir, out_path, args.model, args.scale, args.crf, args.preset)
    else:
        enhance_with_ffmpeg(args.video, out_path, args.profile, args.scale, args.crf, args.preset)

    after = video_info(str(out_path))
    write_metadata(
        out_dir,
        {
            "input_video": str(Path(args.video).resolve()),
            "output_video": str(out_path.resolve()),
            "backend": backend,
            "profile": args.profile,
            "scale": args.scale,
            "model": args.model if backend == "realesrgan" else None,
            "before": before,
            "after": after,
            "usage_note": "Use enhanced_reference.mp4 only for clearer storyboard extraction. Do not use it as the final Seedance video reference.",
        },
    )
    print(out_path)


if __name__ == "__main__":
    main()
